/**
 * Fashion Manager — admin CRUD for products and categories.
 * Uses the shared stack from base_config.js (window.apiUrl, make_request, fetch wrapper, showToast).
 */
(function () {
    'use strict';

    const PAGE_SIZE = 10;
    const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
    const state = { page: 1, search: '', categoryPage: 1, categories: [], allCategories: [], newFiles: [], keepImages: [] };
    const $ = (id) => document.getElementById(id);
    const api = (path) => `${window.apiUrl}${path}`;
    const naira = (n) => '₦' + Number(n || 0).toLocaleString('en-NG');
    const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const modal = (id) => bootstrap.Modal.getOrCreateInstance($(id));
    const toast = (msg, type = 'success') => window.showToast(esc(msg), type);
    const fail = (err) => toast(window.Utils.friendlyError(err), 'danger');

    function debounce(fn, ms = 300) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

    function setBusy(btn, busy, label) {
        btn.disabled = busy;
        btn.innerHTML = busy ? '<span class="spinner-border spinner-border-sm me-2"></span>Saving…' : label;
    }

    function pager(el, meta, onPage) {
        if (!meta || meta.total_pages_count <= 1) { el.innerHTML = meta ? `<span class="text-muted">${meta.total_items_count} item(s)</span>` : ''; return; }
        el.innerHTML = `<span class="text-muted">Page ${meta.current_page_number} of ${meta.total_pages_count} · ${meta.total_items_count} items</span>
            <div class="btn-group btn-group-sm"><button class="btn btn-outline-secondary" ${meta.has_prev_page ? '' : 'disabled'} data-p="${meta.current_page_number - 1}">Prev</button>
            <button class="btn btn-outline-secondary" ${meta.has_next_page ? '' : 'disabled'} data-p="${meta.current_page_number + 1}">Next</button></div>`;
        el.querySelectorAll('button[data-p]').forEach((b) => b.addEventListener('click', () => onPage(Number(b.dataset.p))));
    }

    // ───────────────────────── products
    async function loadProducts() {
        const body = $('productsBody');
        body.innerHTML = '<tr><td colspan="6" class="text-center py-4"><span class="spinner-border spinner-border-sm"></span></td></tr>';
        try {
            const q = new URLSearchParams({ page: state.page, page_size: PAGE_SIZE });
            if (state.search) q.set('search', state.search);
            const data = await window.make_request(api(`/products?${q}`));
            const items = data.products || [];
            body.innerHTML = items.map((p) => `
                <tr>
                  <td>${p.image_urls ? `<img class="thumb" src="${esc(p.image_urls[0])}" alt="" loading="lazy">` : '<div class="thumb"></div>'}</td>
                  <td><div class="fw-medium">${esc(p.name)}</div><div class="fs-xs text-muted">${esc(p.slug)}</div></td>
                  <td>${(p.categories || []).map((c) => `<span class="badge bg-secondary-subtle text-secondary-emphasis me-1">${esc(c.name)}</span>`).join('') || '<span class="text-muted">—</span>'}</td>
                  <td class="text-end">${naira(p.price)}</td>
                  <td class="text-center">${p.stock > 0 ? p.stock : '<span class="badge text-bg-warning">Out</span>'}</td>
                  <td class="text-end text-nowrap">
                    <button class="btn btn-sm btn-outline-dark rounded-pill" data-edit="${p.id}">Edit</button>
                    <button class="btn btn-sm btn-outline-danger rounded-pill" data-del="${p.id}" data-name="${esc(p.name)}">Delete</button>
                  </td>
                </tr>`).join('');
            $('productsEmpty').classList.toggle('d-none', items.length > 0);
            body.querySelectorAll('[data-edit]').forEach((b) => b.addEventListener('click', () => openProduct(b.dataset.edit)));
            body.querySelectorAll('[data-del]').forEach((b) => b.addEventListener('click', () => confirmDelete(`Delete “${b.dataset.name}”?`, 'It will be removed from the shop.', () => deleteProduct(b.dataset.del))));
            pager($('productsPager'), data.page_meta, (p) => { state.page = p; loadProducts(); });
            $('stat-products').textContent = data.page_meta.total_items_count;
            $('stat-out').textContent = items.filter((p) => !p.stock).length;
            $('stat-value').textContent = naira(items.reduce((sum, p) => sum + p.price * p.stock, 0));
        } catch (err) {
            body.innerHTML = '';
            fail(err);
        }
    }

    function renderCategoryChecklist(selected = []) {
        $('productCategories').innerHTML = state.allCategories.length
            ? state.allCategories.map((c) => `<div class="form-check"><input class="form-check-input" type="checkbox" id="pc-${c.id}" value="${esc(c.name)}" ${selected.includes(c.name) ? 'checked' : ''}><label class="form-check-label" for="pc-${c.id}">${esc(c.name)}</label></div>`).join('')
            : '<span class="text-muted fs-sm">Create a category first (optional).</span>';
    }

    function renderImages() {
        $('existingImages').innerHTML = state.keepImages.map((i) => `<span class="img-chip"><img class="thumb thumb-lg" src="${esc(i.url)}" alt=""><button type="button" class="btn-close" data-rm="${i.id}" aria-label="Remove"></button></span>`).join('');
        $('existingImages').querySelectorAll('[data-rm]').forEach((b) => b.addEventListener('click', () => { state.keepImages = state.keepImages.filter((i) => String(i.id) !== b.dataset.rm); renderImages(); }));
        $('newImagePreviews').innerHTML = state.newFiles.map((f, idx) => `<span class="img-chip"><img class="thumb thumb-lg" src="${URL.createObjectURL(f)}" alt=""><button type="button" class="btn-close" data-nf="${idx}" aria-label="Remove"></button></span>`).join('');
        $('newImagePreviews').querySelectorAll('[data-nf]').forEach((b) => b.addEventListener('click', () => { state.newFiles.splice(Number(b.dataset.nf), 1); renderImages(); }));
    }

    async function openProduct(id) {
        $('productForm').reset();
        $('productForm').classList.remove('was-validated');
        state.newFiles = []; state.keepImages = [];
        $('productId').value = id || '';
        $('productModalTitle').textContent = id ? 'Edit product' : 'Add product';
        let selected = [];
        if (id) {
            try {
                const p = await window.make_request(api(`/products/${id}`));
                $('productName').value = p.name; $('productDescription').value = p.description || '';
                $('productPrice').value = p.price; $('productStock').value = p.stock;
                selected = (p.categories || []).map((c) => c.name);
                state.keepImages = p.images || [];
            } catch (err) { return fail(err); }
        }
        renderCategoryChecklist(selected);
        renderImages();
        modal('productModal').show();
    }

    async function saveProduct(e) {
        e.preventDefault();
        const form = $('productForm');
        form.classList.add('was-validated');
        if (!form.checkValidity()) return;
        const id = $('productId').value;
        const fd = new FormData();
        fd.append('name', $('productName').value.trim());
        fd.append('description', $('productDescription').value.trim());
        fd.append('price', $('productPrice').value);
        fd.append('stock', $('productStock').value);
        [...$('productCategories').querySelectorAll('input:checked')].forEach((cb, i) => { fd.append(`categories[${i}][name]`, cb.value); fd.append(`categories[${i}][description]`, cb.value); });
        if (id) { fd.append('image_action', 'replace'); state.keepImages.forEach((i) => fd.append('keep_images[]', i.id)); }
        state.newFiles.forEach((f) => fd.append('images[]', f));

        const btn = $('productSaveBtn');
        setBusy(btn, true);
        try {
            // multipart: let the browser set the boundary (no JSON Content-Type)
            const res = await fetch(api(id ? `/products/${id}` : '/products'), { method: id ? 'PUT' : 'POST', headers: window.getAuthHeaders(), body: fd });
            const json = await res.json().catch(() => ({}));
            if (!res.ok || json.success === false) throw new Error(json.error || json.message || `Request failed (${res.status})`);
            modal('productModal').hide();
            toast(id ? 'Product updated.' : 'Product created.');
            await loadProducts();
        } catch (err) { fail(err); } finally { setBusy(btn, false, 'Save product'); }
    }

    async function deleteProduct(id) {
        try { await window.make_request(api(`/products/${id}`), { method: 'DELETE' }); toast('Product deleted.'); await loadProducts(); }
        catch (err) { fail(err); }
    }

    // ───────────────────────── categories
    async function loadCategories() {
        try {
            const data = await window.make_request(api(`/categories?page=${state.categoryPage}&page_size=${PAGE_SIZE}`));
            state.categories = data.categories || [];
            $('stat-categories').textContent = data.page_meta.total_items_count;
            $('categoriesBody').innerHTML = state.categories.map((c) => `
                <tr><td class="fw-medium">${esc(c.name)}</td><td class="text-muted">${esc(c.description || '—')}</td><td>${esc(c.parent ? c.parent.name : '—')}</td>
                <td class="text-end text-nowrap"><button class="btn btn-sm btn-outline-dark rounded-pill" data-edit="${c.id}">Edit</button>
                <button class="btn btn-sm btn-outline-danger rounded-pill" data-del="${c.id}" data-name="${esc(c.name)}">Delete</button></td></tr>`).join('');
            $('categoriesEmpty').classList.toggle('d-none', state.categories.length > 0);
            $('categoriesBody').querySelectorAll('[data-edit]').forEach((b) => b.addEventListener('click', () => openCategory(b.dataset.edit)));
            $('categoriesBody').querySelectorAll('[data-del]').forEach((b) => b.addEventListener('click', () => confirmDelete(`Delete “${b.dataset.name}”?`, 'Products keep existing but lose this category label in the shop.', () => deleteCategory(b.dataset.del))));
            pager($('categoriesPager'), data.page_meta, (p) => { state.categoryPage = p; loadCategories(); });
        } catch (err) { fail(err); }
    }

    async function loadAllCategories() {
        try {
            const data = await window.make_request(api('/categories?page=1&page_size=100'));
            state.allCategories = data.categories || [];
        } catch (err) { fail(err); }
    }

    function openCategory(id) {
        $('categoryForm').reset();
        $('categoryForm').classList.remove('was-validated');
        $('categoryId').value = id || '';
        $('categoryModalTitle').textContent = id ? 'Edit category' : 'Add category';
        const current = state.allCategories.find((c) => String(c.id) === String(id));
        $('categoryParent').innerHTML = '<option value="">None (top level)</option>' +
            state.allCategories.filter((c) => String(c.id) !== String(id)).map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join('');
        if (current) { $('categoryName').value = current.name; $('categoryDescription').value = current.description || ''; $('categoryParent').value = current.parent_id || ''; }
        modal('categoryModal').show();
    }

    async function saveCategory(e) {
        e.preventDefault();
        const form = $('categoryForm');
        form.classList.add('was-validated');
        if (!form.checkValidity()) return;
        const id = $('categoryId').value;
        const btn = $('categorySaveBtn');
        setBusy(btn, true);
        try {
            await window.make_request(api(id ? `/categories/${id}` : '/categories'), {
                method: id ? 'PUT' : 'POST',
                body: JSON.stringify({ name: $('categoryName').value.trim(), description: $('categoryDescription').value.trim(), parent_id: $('categoryParent').value || null }),
            });
            modal('categoryModal').hide();
            toast(id ? 'Category updated.' : 'Category created.');
            await Promise.all([loadAllCategories(), loadCategories()]);
        } catch (err) { fail(err); } finally { setBusy(btn, false, 'Save category'); }
    }

    async function deleteCategory(id) {
        try { await window.make_request(api(`/categories/${id}`), { method: 'DELETE' }); toast('Category deleted.'); await Promise.all([loadAllCategories(), loadCategories()]); }
        catch (err) { fail(err); }
    }

    // ───────────────────────── shared confirm dialog
    function confirmDelete(title, text, action) {
        $('confirmTitle').textContent = title;
        $('confirmText').textContent = text;
        const ok = $('confirmOk');
        const fresh = ok.cloneNode(true);       // drop previous handlers
        ok.replaceWith(fresh);
        fresh.addEventListener('click', async () => { fresh.disabled = true; modal('confirmModal').hide(); await action(); fresh.disabled = false; });
        modal('confirmModal').show();
    }

    // ───────────────────────── init
    function onFilesChosen(e) {
        for (const f of e.target.files) {
            if (!/^image\//.test(f.type)) { toast(`${f.name} is not an image.`, 'danger'); continue; }
            if (f.size > MAX_IMAGE_BYTES) { toast(`${f.name} is larger than 5 MB.`, 'danger'); continue; }
            state.newFiles.push(f);
        }
        e.target.value = '';
        renderImages();
    }

    document.addEventListener('DOMContentLoaded', async () => {
        if (!(await window.authRequired(['admin']))) return;   // admins/devs only
        $('addProductBtn').addEventListener('click', () => openProduct(null));
        $('addCategoryBtn').addEventListener('click', () => openCategory(null));
        $('productForm').addEventListener('submit', saveProduct);
        $('categoryForm').addEventListener('submit', saveCategory);
        $('productImages').addEventListener('change', onFilesChosen);
        $('productSearch').addEventListener('input', debounce((e) => { state.search = e.target.value.trim(); state.page = 1; loadProducts(); }));
        await loadAllCategories();
        await Promise.all([loadProducts(), loadCategories()]);
    });
})();
