(() => {
    'use strict';
    const $ = (id) => document.getElementById(id);
    const dialog = $('pdf-dialog'), stage = $('pdf-stage'), status = $('pdf-status');
    const download = $('pdf-download'), newTab = $('pdf-new-tab'), retry = $('pdf-retry');
    const controls = $('pdf-controls');
    let row = null, controller = null, objectUrl = null, previousFocus = null;
    let loadingTask = null, documentPdf = null, renderTask = null, library = null;
    let session = 0, paint = 0, pageNumber = 1, zoom = 1, statusKey = '', rendering = false;
    let translate = (key) => key;

    function updateLanguage(t) {
        translate = t;
        $('pdf-close').setAttribute('aria-label', t('closePreview'));
        for (const [id, key] of [['pdf-previous','previousPage'], ['pdf-next','nextPage'],
            ['pdf-zoom-out','zoomOut'], ['pdf-zoom-in','zoomIn']]) {
            $(id).setAttribute('aria-label', t(key));
            $(id).title = t(key);
        }
        status.textContent = statusKey ? t(statusKey) : '';
        updateControls();
    }

    function updateControls() {
        $('pdf-previous').disabled = rendering || !documentPdf || pageNumber <= 1;
        $('pdf-next').disabled = rendering || !documentPdf || pageNumber >= documentPdf.numPages;
        $('pdf-zoom-out').disabled = rendering || zoom <= 1;
        $('pdf-zoom-in').disabled = rendering || zoom >= 3;
        $('pdf-page-number').textContent = documentPdf ? `${pageNumber} / ${documentPdf.numPages}` : '';
        stage.querySelector('canvas')?.setAttribute('aria-label',
            `${translate('preview')}: ${row?.subject || ''}, ${pageNumber}`);
    }

    function release() {
        session++;
        paint++;
        controller?.abort(); controller = null;
        renderTask?.cancel(); renderTask = null;
        loadingTask?.destroy().catch(() => {}); loadingTask = null;
        documentPdf = null;
        stage.replaceChildren();
        controls.hidden = true;
        rendering = false;
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        objectUrl = null;
    }

    function showError(error) {
        statusKey = error.tooLarge ? 'pdfTooLarge' : 'pdfError';
        status.textContent = translate(statusKey);
        status.classList.remove('is-loading');
        retry.hidden = !!error.tooLarge;
    }

    async function renderPage() {
        if (!documentPdf || !dialog.open) return;
        const currentSession = session, currentPaint = ++paint, pdf = documentPdf;
        renderTask?.cancel();
        rendering = true;
        updateControls();
        statusKey = 'pdfLoading';
        status.textContent = translate(statusKey);
        status.classList.add('is-loading');
        try {
            const page = await pdf.getPage(pageNumber);
            if (session !== currentSession || paint !== currentPaint) return;
            const original = page.getViewport({scale: 1});
            const width = Math.max(200, stage.clientWidth - 24);
            const viewport = page.getViewport({scale: width / original.width * zoom});
            // Bound canvas memory on phones, including high-density displays.
            const density = Math.min(window.devicePixelRatio || 1, 2,
                Math.sqrt(4000000 / (viewport.width * viewport.height)));
            const canvas = document.createElement('canvas');
            canvas.width = Math.max(1, Math.floor(viewport.width * density));
            canvas.height = Math.max(1, Math.floor(viewport.height * density));
            canvas.style.width = `${viewport.width}px`;
            canvas.style.height = `${viewport.height}px`;
            canvas.setAttribute('role', 'img');
            const task = page.render({canvasContext: canvas.getContext('2d'), viewport,
                transform: [density, 0, 0, density, 0, 0]});
            renderTask = task;
            await task.promise;
            if (session !== currentSession || paint !== currentPaint) return;
            stage.replaceChildren(canvas);
            stage.scrollTo?.(0, 0);
            statusKey = '';
            status.textContent = '';
        } catch (error) {
            if (session === currentSession && paint === currentPaint && error.name !== 'RenderingCancelledException') showError(error);
        } finally {
            if (session === currentSession && paint === currentPaint) {
                renderTask = null;
                rendering = false;
                status.classList.remove('is-loading');
                updateControls();
            }
        }
    }

    async function load() {
        release();
        const currentSession = session;
        const pending = new AbortController();
        controller = pending;
        pageNumber = 1; zoom = 1;
        statusKey = 'pdfLoading';
        status.textContent = translate(statusKey);
        status.classList.add('is-loading');
        retry.hidden = true;
        const encoded = encodeURIComponent(row.ada);
        download.href = `/download/${encoded}`;
        download.download = `${row.ada}.pdf`;
        // A real URL remains valid even after this dialog closes/revokes its Blob.
        newTab.href = `/document/${encoded}`;
        try {
            const response = await fetch(`/document/${encoded}`, {signal: pending.signal});
            if (!response.ok) {
                const error = new Error('PDF request failed');
                error.tooLarge = response.status === 413;
                throw error;
            }
            const blob = await response.blob();
            if (session !== currentSession || !dialog.open) return;
            if (blob.type.split(';')[0] !== 'application/pdf') throw new Error('Invalid PDF');
            objectUrl = URL.createObjectURL(blob);
            download.href = objectUrl;
            library ||= import('/static/vendor/pdfjs/pdf.min.mjs').catch(error => {library = null; throw error;});
            const pdfjs = await library;
            const bytes = new Uint8Array(await blob.arrayBuffer());
            if (session !== currentSession || !dialog.open) return;
            pdfjs.GlobalWorkerOptions.workerSrc = '/static/vendor/pdfjs/pdf.worker.min.mjs';
            pdfjs.GlobalWorkerOptions.rendererSrc = '/static/vendor/pdfjs/pdf.renderer.min.mjs';
            loadingTask = pdfjs.getDocument({data: bytes, isEvalSupported: false,
                cMapUrl: '/static/vendor/pdfjs/cmaps/', cMapPacked: true,
                standardFontDataUrl: '/static/vendor/pdfjs/standard_fonts/',
                wasmUrl: '/static/vendor/pdfjs/wasm/'});
            const loaded = await loadingTask.promise;
            if (session !== currentSession || !dialog.open) { loaded.destroy().catch(() => {}); return; }
            documentPdf = loaded;
            controls.hidden = false;
            await renderPage();
        } catch (error) {
            if (session !== currentSession || error.name === 'AbortError') return;
            showError(error);
        } finally {
            if (session === currentSession) {
                controller = null;
                status.classList.remove('is-loading');
            }
        }
    }

    $('pdf-previous').addEventListener('click', () => {if (pageNumber > 1) {pageNumber--; renderPage();}});
    $('pdf-next').addEventListener('click', () => {if (documentPdf && pageNumber < documentPdf.numPages) {pageNumber++; renderPage();}});
    $('pdf-zoom-in').addEventListener('click', () => {zoom = Math.min(3, zoom + .5); renderPage();});
    $('pdf-zoom-out').addEventListener('click', () => {zoom = Math.max(1, zoom - .5); renderPage();});
    let resizeTimer;
    window.addEventListener('resize', () => {clearTimeout(resizeTimer); resizeTimer = setTimeout(renderPage, 150);});
    $('pdf-close').addEventListener('click', () => dialog.close());
    retry.addEventListener('click', load);
    dialog.addEventListener('click', event => {
        if (event.target !== dialog) return;
        const bounds = dialog.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
    dialog.addEventListener('close', () => {
        release(); row = null;
        document.body.classList.remove('pdf-open');
        if (previousFocus?.isConnected) previousFocus.focus({preventScroll: true});
        else $('main-content').focus({preventScroll: true});
    });
    window.pdfPreview = {updateLanguage, open(decision, t) {
        row = decision; previousFocus = document.activeElement;
        $('pdf-title').textContent = decision.subject;
        updateLanguage(t);
        if (!dialog.open) dialog.showModal();
        document.body.classList.add('pdf-open');
        load();
    }};
})();
