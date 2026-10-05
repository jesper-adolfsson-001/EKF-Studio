import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {flushSync} from 'react-dom';
import {
  MDXEditor, headingsPlugin, listsPlugin, quotePlugin, linkPlugin, linkDialogPlugin,
  imagePlugin, tablePlugin, thematicBreakPlugin, markdownShortcutPlugin, toolbarPlugin,
  codeBlockPlugin, useCodeBlockEditorContext, UndoRedo, BoldItalicUnderlineToggles,
  BlockTypeSelect, ListsToggle, CreateLink, InsertImage, InsertTable, InsertCodeBlock,
  $createImageNode, $isImageNode, realmPlugin, addImportVisitor$, addExportVisitor$,
  activeEditor$, rootEditor$, insertMarkdown$
} from '@mdxeditor/editor';
import {useLexicalComposerContext} from '@lexical/react/LexicalComposerContext';
import {$getNodeByKey, $createParagraphNode, $getSelection, $isRangeSelection, $getRoot} from 'lexical';
import {marked} from 'marked';
import DOMPurify from 'dompurify';
import '@mdxeditor/editor/style.css';
import './markdown.css';

// All local references resolve beside the Markdown, including when browsing a Git revision.
export function assetUrl(value, path, ref = '', download = false) {
  if (!value || /[\u0000-\u001f\\]/.test(value)) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (/^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(value)) return '';
  if (value.startsWith('#')) return download ? value : '';
  try {
    const parts = value.startsWith('/') ? [] : path.split('/').slice(0, -1);
    const [pathname, fragment] = value.split('#');
    for (const part of decodeURIComponent(pathname).split('/')) {
      if (!part || part === '.') continue;
      if (part === '..') {if (!parts.length) return ''; parts.pop();}
      else {if (part.startsWith('.') || /[\\\u0000-\u001f]/.test(part)) return ''; parts.push(part);}
    }
    const query = new URLSearchParams({path: parts.join('/')});
    if (ref) query.set('ref', ref);
    if (download) query.set('download', '1');
    return '/api/asset?' + query + (fragment ? '#' + encodeURIComponent(fragment) : '');
  } catch {return '';}
}

export function renderMarkdown(source, path, ref = '') {
  const fragment = DOMPurify.sanitize(marked.parse(source, {gfm:true}), {
    RETURN_DOM_FRAGMENT:true,
    ALLOWED_TAGS:['p','br','hr','h1','h2','h3','h4','h5','h6','strong','b','em','i','u','s','del','blockquote','ul','ol','li','pre','code','a','img','table','thead','tbody','tr','th','td','input','sup','sub','div','span'],
    ALLOWED_ATTR:['href','src','alt','title','width','height','class','align','start','type','checked','disabled'],
    ALLOW_DATA_ATTR:false, ALLOW_ARIA_ATTR:false
  });
  for (const element of fragment.querySelectorAll('*')) {
    if (element.tagName !== 'IMG') {element.removeAttribute('class'); element.removeAttribute('align');}
    if (element.tagName === 'INPUT') {element.type = 'checkbox'; element.disabled = true;}
    if (element.tagName === 'IMG') {
      const alignment = /(?:^|\s)ekf-image-(left|center|right)(?:\s|$)/.exec(element.className)?.[1] || element.getAttribute('align');
      element.removeAttribute('class');element.removeAttribute('align');
      if (['left','center','right'].includes(alignment)) element.className = 'ekf-image-' + alignment;
      for (const attr of ['width','height']) {
        const value = element.getAttribute(attr);
        if (value && (!/^\d+$/.test(value) || +value < 1 || +value > 10000)) element.removeAttribute(attr);
      }
      const url = assetUrl(element.getAttribute('src'), path, ref);
      if (url) element.src = url; else element.removeAttribute('src');
      element.loading = 'lazy';element.decoding = 'async';element.referrerPolicy = 'no-referrer';
    }
    if (element.tagName === 'A') {
      const href = element.getAttribute('href') || '';
      const url = /^mailto:[^\s]+$/i.test(href) ? href : assetUrl(href, path, ref, true);
      if (url) element.href = url; else element.removeAttribute('href');
      if (/^https?:/i.test(url)) {element.target = '_blank';element.rel = 'noopener noreferrer';}
    }
  }
  const container = document.createElement('div');container.append(fragment);return container.innerHTML;
}

const imageClass = node => node.getRest().find(a => a.name === 'class' || a.name === 'className')?.value || '';
function ImageControls({nodeKey, width, height, alt}) {
  const [editor] = useLexicalComposerContext();
  const [alignment, setAlignment] = useState('left');
  const controls = useRef(null);
  useLayoutEffect(() => {
    const wrapper = controls.current?.closest('[data-editor-block-type="image"]'), img = wrapper?.querySelector('img');
    if (!img) return;
    // The library positions handles around its wrapper. Our full-width wrapper also
    // contains the controls, so anchor the handles to the actual image rectangle.
    const measure = () => {
      const imageBox = img.getBoundingClientRect(), box = wrapper.getBoundingClientRect();
      for (const [key,value] of Object.entries({left:imageBox.left-box.left,top:imageBox.top-box.top,width:imageBox.width,height:imageBox.height})) wrapper.style.setProperty('--image-'+key,value+'px');
    };
    const observer = new ResizeObserver(measure);observer.observe(img);observer.observe(wrapper);measure();
    return () => observer.disconnect();
  }, [nodeKey,alignment]);
  useEffect(() => editor.getEditorState().read(() => {
    const node = $getNodeByKey(nodeKey);
    if ($isImageNode(node)) setAlignment(/ekf-image-(left|center|right)/.exec(imageClass(node))?.[1] || 'left');
  }), [editor,nodeKey]);
  const update = callback => editor.update(() => {const node = $getNodeByKey(nodeKey);if ($isImageNode(node)) callback(node);});
  const dimension = value => /^\d+$/.test(value) ? Math.max(1,Math.min(10000,+value)) : 'inherit';
  return <div ref={controls} className="ekf-image-controls" contentEditable={false} onKeyDown={e => e.stopPropagation()}>
    <label>Align <select aria-label="Image alignment" value={alignment} onChange={e => {
      const value = e.target.value;setAlignment(value);
      update(node => node.replace($createImageNode({src:node.getSrc(),altText:node.getAltText(),title:node.getTitle(),width:node.getWidth(),height:node.getHeight(),
        rest:[{type:'mdxJsxAttribute',name:'class',value:'ekf-image-'+value}]})));
    }}><option value="left">Left</option><option value="center">Center</option><option value="right">Right</option></select></label>
    <label>W <input aria-label="Image width" type="number" min="1" max="10000" placeholder="Auto" value={width === 'inherit' ? '' : width ?? ''} onChange={e => update(n => n.setWidthAndHeight(dimension(e.target.value),n.getHeight()))}/></label>
    <label>H <input aria-label="Image height" type="number" min="1" max="10000" placeholder="Auto" value={height === 'inherit' ? '' : height ?? ''} onChange={e => update(n => n.setWidthAndHeight(n.getWidth(),dimension(e.target.value)))}/></label>
    <label className="ekf-image-alt">Alt <input aria-label="Image description" value={alt} onChange={e => update(n => n.setAltText(e.target.value))}/></label>
    <button type="button" onClick={() => update(n => n.setWidthAndHeight('inherit','inherit'))}>Reset size</button>
    <button type="button" aria-label="Remove image" onClick={() => update(n => n.remove())}>Remove</button>
  </div>;
}

// Preserve relative URLs and alignment on HTML image imports. Export with DOM escaping.
const portableImages = realmPlugin({init(realm) {
  realm.pub(addImportVisitor$, {
    priority:100,
    testNode:node => node.type === 'html' && /^\s*<img\b/i.test(node.value),
    visitNode({mdastNode,lexicalParent}) {
      const doc = new DOMParser().parseFromString(mdastNode.value,'text/html'), img = doc.querySelector('img');
      if (!img) return;
      const alignment = /ekf-image-(left|center|right)/.exec(img.className)?.[1] || img.getAttribute('align');
      const node = $createImageNode({src:img.getAttribute('src')||'',altText:img.alt,title:img.title,width:img.width||undefined,height:img.height||undefined,
        rest:['left','center','right'].includes(alignment) ? [{type:'mdxJsxAttribute',name:'class',value:'ekf-image-'+alignment}] : []});
      if (lexicalParent.getType() === 'root') lexicalParent.append($createParagraphNode().append(node));else lexicalParent.append(node);
    }
  });
  realm.pub(addExportVisitor$, {
    priority:100, testLexicalNode:$isImageNode,
    visitLexicalNode({mdastParent,lexicalNode:node,actions}) {
      if (!node.shouldBeSerializedAsElement()) {
        actions.appendToParent(mdastParent,{type:'image',url:node.getSrc(),alt:node.getAltText(),title:node.getTitle()});return;
      }
      const img = document.implementation.createHTMLDocument('').createElement('img');
      img.setAttribute('src',node.getSrc());img.alt = node.getAltText();
      if (node.getTitle()) img.title = node.getTitle();
      for (const [key,value] of [['width',node.getWidth()],['height',node.getHeight()]]) if (value !== 'inherit') img.setAttribute(key,String(value));
      const alignment = /ekf-image-(left|center|right)/.exec(imageClass(node))?.[1];
      if (alignment) img.className = 'ekf-image-'+alignment;
      actions.appendToParent(mdastParent,{type:'html',value:img.outerHTML.replace(/>$/,' />')});
    }
  });
}});

function PlainCode({code,language,focusEmitter}) {
  const {setCode} = useCodeBlockEditorContext();const ref = useRef(null);
  useEffect(() => {focusEmitter.subscribe(() => ref.current?.focus());},[focusEmitter]);
  return <div className="ekf-code-block"><small>{language || 'Code'}</small><textarea ref={ref} aria-label="Code block" value={code} onChange={e => setCode(e.target.value)} onKeyDown={e => e.stopPropagation()}/></div>;
}

export function mountMarkdownEditor(host, textarea, getPath) {
  const files = new Map();const root = createRoot(host);let disposed = false, currentMode = 'rich';
  const stage = async file => {
    if (disposed) throw new Error('The editor was closed.');
    if (file.size > 10*1024*1024) throw new Error('Each attachment must be at most 10 MB.');
    if (files.size >= 50 || [...files.values()].reduce((s,f) => s+f.file.size,0)+file.size > 20*1024*1024) throw new Error('Attach at most 50 files totalling 20 MB per save.');
    const clean = file.name.normalize('NFKD').replace(/[^a-zA-Z0-9._-]/g,'-').replace(/^[^a-zA-Z0-9]+/,'').slice(0,120) || 'attachment';
    const dot = clean.lastIndexOf('.'), suffix = dot > 0 ? clean.slice(dot).replace(/\.+$/,'') : '';
    const name = (dot > 0 ? clean.slice(0,dot) : clean).replace(/\.+$/,'') + '-' + crypto.randomUUID().slice(0,12) + suffix;
    const url = 'assets/'+name;files.set(url,{name,file,preview:URL.createObjectURL(file)});return url;
  };
  const preview = url => files.get(url)?.preview || assetUrl(url,getPath());
  let insertRich;
  const attachmentInsertion = realmPlugin({init(realm) {
    insertRich = markdown => {
      const editor = realm.getValue(activeEditor$) || realm.getValue(rootEditor$);
      realm.pub(activeEditor$,editor);
      editor?.update(() => {
        const selection = $getSelection();
        // Adding an attachment must not replace a selected image or selected text.
        if ($isRangeSelection(selection)) {
          selection.anchor.set(selection.focus.key,selection.focus.offset,selection.focus.type);
        } else $getRoot().selectEnd();
        realm.pub(insertMarkdown$,markdown);
      }, {discrete:true});
    };
  }});
  function Editor() {
    const ref = useRef(null), imageInput = useRef(null), fileInput = useRef(null);
    const [mode,setMode] = useState('rich');const [generation,setGeneration] = useState(0);
    const [message,setMessage] = useState('');
    const switchMode = next => {
      if (next === mode) return;
      if (next === 'rich') {setGeneration(g => g+1);setMessage('');}
      currentMode = next;textarea.hidden = next !== 'source';setMode(next);
    };
    const insert = markdown => {
      if (currentMode === 'source') {
        textarea.setRangeText(markdown,textarea.selectionStart,textarea.selectionEnd,'end');textarea.focus();
      } else insertRich(markdown);
    };
    const attachFiles = async (selected, images) => {
      try {
        for (const file of selected) {
          const isImage = images ?? /^image\/(png|jpeg|gif|webp|avif|svg\+xml)$/.test(file.type);
          if (isImage && !/^image\/(png|jpeg|gif|webp|avif|svg\+xml)$/.test(file.type)) throw new Error('Choose a PNG, JPEG, GIF, WebP, AVIF or SVG image.');
          const url = await stage(file), label = file.name.replace(/[\\[\]<>\r\n]/g,'_');
          insert(`\n\n${isImage?'!':''}[${label}](${url})\n\n`);
        }
        setMessage('Attachments will be saved with this item.');
      } catch (e) {setMessage(e.message);}
    };
    const attach = event => {
      const selected = [...event.target.files], images = event.target === imageInput.current;
      event.target.value = '';void attachFiles(selected,images);
    };
    const transferFiles = event => {
      const selected = [...((event.clipboardData || event.dataTransfer)?.files || [])];
      if (!selected.length) return;
      event.preventDefault();event.stopPropagation();void attachFiles(selected);
    };
    const plugins = [headingsPlugin(),listsPlugin(),quotePlugin(),linkPlugin(),linkDialogPlugin(),attachmentInsertion(),
      imagePlugin({EditImageToolbar:ImageControls,allowSetImageDimensions:true,imagePreviewHandler:async url => preview(url)}), portableImages(),tablePlugin(),thematicBreakPlugin(),
      codeBlockPlugin({codeBlockEditorDescriptors:[{priority:0,match:()=>true,Editor:PlainCode}]}),markdownShortcutPlugin(),
      toolbarPlugin({toolbarContents:() => <><UndoRedo/><BlockTypeSelect/><BoldItalicUnderlineToggles/><ListsToggle/><CreateLink/><InsertImage/><InsertTable/><InsertCodeBlock/></>})];
    return <div className="ekf-markdown-editor" onPasteCapture={transferFiles} onDropCapture={transferFiles} onDragOver={e => {if (e.dataTransfer.types.includes('Files')) e.preventDefault();}}>
      <div className="ekf-editor-actions">
        <div role="group" aria-label="Markdown editing mode"><button type="button" aria-pressed={mode==='rich'} onClick={() => switchMode('rich')}>Rich text</button><button type="button" aria-pressed={mode==='source'} onClick={() => switchMode('source')}>Markdown source</button></div>
        <button type="button" onClick={() => imageInput.current.click()}>Add image</button><button type="button" onClick={() => fileInput.current.click()}>Attach file</button>
        <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/gif,image/webp,image/avif,image/svg+xml" multiple hidden aria-label="Upload images" onChange={attach}/>
        <input ref={fileInput} type="file" multiple hidden aria-label="Upload attachments" onChange={attach}/>
      </div>
      <p className="ekf-editor-help">Images and files go in assets/ beside this Markdown file. Select an image to resize it, or use its width, height and alignment controls. Leave one dimension blank to keep its proportions.</p>
      <p className="ekf-editor-message" role="status">{message}</p>
      {mode==='rich' && <MDXEditor key={generation} ref={ref} markdown={textarea.value} trim={false} className="ekf-rich-editor" contentEditableClassName="markdown ekf-editable" overlayContainer={host}
        plugins={plugins} onChange={(value,initial) => {if (!initial) textarea.value = value;}}
        onError={() => {setMessage('This content needs Markdown source mode. Your original text has been preserved.');currentMode='source';textarea.hidden=false;setMode('source');}}/>}
    </div>;
  }
  textarea.hidden = true;
  flushSync(() => root.render(<Editor/>));
  return {
    async uploads() {
      const selected = [...files.entries()].filter(([url]) => textarea.value.includes(url));
      return Promise.all(selected.map(async ([,item]) => {
        const bytes = new Uint8Array(await item.file.arrayBuffer());let binary = '';
        for (let i=0;i<bytes.length;i+=8192) binary += String.fromCharCode(...bytes.subarray(i,i+8192));
        return {name:item.name,content:btoa(binary)};
      }));
    },
    dispose() {disposed=true;root.unmount();for (const item of files.values()) URL.revokeObjectURL(item.preview);files.clear();}
  };
}
