import React, { useEffect, useRef, useState } from 'react';
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, LoaderCircle } from 'lucide-react';
GlobalWorkerOptions.workerSrc = '/assets/pdf.worker.min.mjs';

export const PdfReader = ({ url }) => {
  const [document, setDocument] = useState(null);
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [width, setWidth] = useState(800);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const canvas = useRef(); const frame = useRef();
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(220, entry.contentRect.width - 24)));
    if (frame.current) observer.observe(frame.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const task = getDocument({ url, standardFontDataUrl: '/assets/pdf-fonts/' });
    let cancelled = false;
    task.promise.then(doc => { if (!cancelled) setDocument(doc); }).catch(() => { if (!cancelled) { setError('PDF could not be loaded. The direct file and download links remain available.'); setBusy(false); } });
    return () => { cancelled = true; task.destroy(); };
  }, [url]);
  useEffect(() => {
    if (!document || !canvas.current) return;
    let cancelled = false; let render;
    setBusy(true); setError('');
    document.getPage(page).then(pdfPage => {
      if (cancelled || !canvas.current) return;
      const base = pdfPage.getViewport({ scale: 1 });
      const density = Math.min(window.devicePixelRatio || 1, 1.5);
      const viewport = pdfPage.getViewport({ scale: width / base.width * zoom * density });
      canvas.current.width = viewport.width; canvas.current.height = viewport.height;
      canvas.current.style.width = `${viewport.width / density}px`;
      canvas.current.style.height = `${viewport.height / density}px`;
      render = pdfPage.render({ canvasContext: canvas.current.getContext('2d'), viewport });
      return render.promise;
    }).then(() => { if (!cancelled) setBusy(false); }).catch(e => {
      if (!cancelled && e.name !== 'RenderingCancelledException') { setError('This PDF page could not render. Try another page or download the file.'); setBusy(false); }
    });
    return () => { cancelled = true; render?.cancel(); };
  }, [document, page, width, zoom]);
  return <div className="native-pdf-reader" data-testid="whitepaper-pdf-frame"><div className="pdf-reader-toolbar"><button title="Previous PDF page" data-testid="pdf-previous-page" disabled={!document || page === 1} onClick={() => setPage(p => p - 1)}><ChevronLeft size={17} /></button><span data-testid="pdf-page-count">{page} / {document?.numPages || '—'}</span><button title="Next PDF page" data-testid="pdf-next-page" disabled={!document || page >= document.numPages} onClick={() => setPage(p => p + 1)}><ChevronRight size={17} /></button><span className="pdf-reader-spacer" /><button title="Zoom out" data-testid="pdf-zoom-out" disabled={zoom <= .6} onClick={() => setZoom(z => Math.max(.6, z - .1))}><ZoomOut size={16} /></button><span data-testid="pdf-zoom-level">{Math.round(zoom * 100)}%</span><button title="Zoom in" data-testid="pdf-zoom-in" disabled={zoom >= 1.5} onClick={() => setZoom(z => Math.min(1.5, z + .1))}><ZoomIn size={16} /></button></div><div className="pdf-canvas-scroller" ref={frame}>{busy && <div className="pdf-render-status" data-testid="pdf-rendering"><LoaderCircle size={15} className="animate-spin" />Rendering PDF…</div>}{error && <p className="market-error" role="alert" data-testid="pdf-render-error">{error}</p>}<canvas data-testid="pdf-page-canvas" ref={canvas} aria-label={`FEELESS PDF page ${page}`} />{!busy && !error && document && <span className="sr-only" data-testid="pdf-page-ready">PDF page {page} rendered</span>}</div></div>;
};