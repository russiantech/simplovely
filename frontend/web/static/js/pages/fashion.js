/**
 * Enhanced Fashion Products JavaScript Implementation
 * Professional integration with backend API for dynamic category-based product management
 */


// Set API base URL: use production if on production domain, else use local/dev
const apiURL = (
    window.location.hostname === "simplylovely.ng" ||
    window.location.hostname.endsWith(".simplylovely.ng")
)
        ? "https://api.simplylovely.ng/api"
        : (window.apiURL || "http://localhost:5001/api");

class FashionProductsAPI {
    constructor(baseURL = apiURL) {
        this.baseURL = baseURL;
        this.currentCategory = 'all';
        this.products = [];
        this.categories = [];
        this.loading = false;
        this.cache = new Map(); // Cache for performance
        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            this.setupEventListeners();
            await this.loadInitialData();
            this.renderInitialTabs();
        } catch (error) {
            console.error('Initialization failed:', error);
            this.showError('Failed to initialize application');
        }
    }

    /**
     * Setup event listeners for tabs and interactions
     */
    setupEventListeners() {
        // Tab switching for categories
        document.querySelectorAll('[data-bs-toggle="pill"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (event) => {
                const targetId = event.target.getAttribute('data-bs-target');
                this.handleCategorySwitch(targetId);
            });
        });

        // Handle service card clicks
        document.addEventListener('click', (event) => {
            if (event.target.closest('.category-card')) {
                event.preventDefault();
                const serviceElement = event.target.closest('.category-card');
                this.handleServiceClick(serviceElement);
            }
        });

        // Handle product interactions
        document.addEventListener('click', (event) => {
            const productLink = event.target.closest('a[data-product-id]');
            if (productLink) {
                event.preventDefault();
                const productId = productLink.getAttribute('data-product-id');
                this.viewProduct(productId);
            }
        });
    }

    /**
     * Load initial data from backend
     */
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadCategories(),
                this.loadFashionServices(),
                this.loadProducts('all')
            ]);
        } catch (error) {
            console.error('Failed to load initial data:', error);
            throw error;
        }
    }

    /**
     * Load categories from backend and map to tabs
     */
    async loadCategories() {
        const cacheKey = 'categories';
        if (this.cache.has(cacheKey)) {
            this.categories = this.cache.get(cacheKey);
            return;
        }

        try {
            const response = await fetch(`${this.baseURL}/categories`);
            const data = await response.json();
            
            if (data.success && data.categories) {
                // Map backend categories to frontend structure
                this.categories = this.normalizeCategories(data.categories);
                
                // Ensure all categories have valid slugs
                Object.keys(this.categories).forEach(key => {
                    const category = this.categories[key];
                    if (category.slug && !this.isValidCSSSelector(category.slug)) {
                        console.warn(`Fixing invalid slug for category ${category.name}: ${category.slug}`);
                        category.slug = this.createValidSlug(category.name);
                        
                        // Update the key in categories object if needed
                        if (key !== category.slug && key !== 'all' && !this.isDefaultCategory(key)) {
                            delete this.categories[key];
                            this.categories[category.slug] = category;
                        }
                    }
                });
                
                this.cache.set(cacheKey, this.categories);
                this.updateCategoryTabs();
            } else {
                // Fallback categories if backend fails
                this.categories = this.getDefaultCategories();
                console.warn('Using default categories due to backend error');
            }
        } catch (error) {
            console.error('Error loading categories:', error);
            this.categories = this.getDefaultCategories();
            throw error;
        }
    }

    /**
     * Normalize categories from backend to match frontend expectations
     */
    normalizeCategories(backendCategories) {
        const categoryMap = {
            'women': ['women', 'female', 'ladies', 'womens'],
            'men': ['men', 'male', 'mens', 'gentlemen'],
            'children': ['children', 'kids', 'child', 'baby', 'infant'],
            'unisex': ['unisex', 'universal', 'both']
        };

        const normalized = {
            all: { id: 'all', name: 'All', slug: 'all', products: [] },
            women: { id: null, name: 'Women', slug: 'women', products: [] },
            men: { id: null, name: 'Men', slug: 'men', products: [] },
            children: { id: null, name: 'Children', slug: 'children', products: [] }
        };

        // Map backend categories to normalized structure
        backendCategories.forEach(category => {
            const categoryName = category.name.toLowerCase();
            let mapped = false;

            for (const [key, keywords] of Object.entries(categoryMap)) {
                if (keywords.some(keyword => categoryName.includes(keyword))) {
                    if (normalized[key]) {
                        normalized[key].id = category.id;
                        normalized[key].name = category.name;
                        normalized[key].backendCategory = category;
                        mapped = true;
                        break;
                    }
                }
            }

            // If no mapping found, add as custom category
            if (!mapped) {
                const slug = this.createValidSlug(category.name);
                normalized[slug] = {
                    id: category.id,
                    name: category.name,
                    slug: slug,
                    backendCategory: category,
                    products: []
                };
            }
        });

        return normalized;
    }

    /**
     * Create valid CSS selector-compatible slug from category name
     */
    createValidSlug(name) {
        return name
            .toLowerCase()
            .trim()
            // Replace spaces and special characters with hyphens
            .replace(/[^a-z0-9]+/g, '-')
            // Remove leading/trailing hyphens
            .replace(/^-+|-+$/g, '')
            // Ensure it doesn't start with a number (CSS requirement)
            .replace(/^(\d)/, 'cat-$1')
            // Fallback if empty
            || 'category';
    }

    /**
     * Get default categories as fallback
     */
    getDefaultCategories() {
        return {
            all: { id: 'all', name: 'All', slug: 'all', products: [] },
            women: { id: null, name: 'Women', slug: 'women', products: [] },
            men: { id: null, name: 'Men', slug: 'men', products: [] },
            children: { id: null, name: 'Children', slug: 'children', products: [] }
        };
    }

    /**
     * Update category tabs with actual backend data
     */
    updateCategoryTabs() {
        const tabsContainer = document.querySelector('.nav-pills');
        if (!tabsContainer) return;

        // Keep the existing tabs but clean up any dynamic ones first
        const existingDynamicTabs = tabsContainer.querySelectorAll('.nav-item[data-dynamic="true"]');
        existingDynamicTabs.forEach(tab => tab.remove());

        // Clean up corresponding tab panes
        const existingDynamicPanes = document.querySelectorAll('.tab-pane[data-dynamic="true"]');
        existingDynamicPanes.forEach(pane => pane.remove());

        Object.entries(this.categories).forEach(([key, category]) => {
            if (key === 'all') return; // Skip 'all' as it's already there

            // Only add categories that have valid data and aren't already represented
            if ((category.id || category.backendCategory) && !this.isDefaultCategory(key)) {
                try {
                    const tabItem = this.createCategoryTab(category);
                    const moreLink = tabsContainer.querySelector('.nav.ms-auto');
                    if (moreLink) {
                        tabsContainer.insertBefore(tabItem, moreLink);
                    } else {
                        tabsContainer.appendChild(tabItem);
                    }
                } catch (error) {
                    console.error(`Failed to create tab for category ${category.name}:`, error);
                }
            }
        });
    }

    /**
     * Check if category is one of the default categories
     */
    isDefaultCategory(categoryKey) {
        const defaultCategories = ['all', 'women', 'men', 'children'];
        return defaultCategories.includes(categoryKey);
    }

    /**
     * Create a category tab element
     */
    createCategoryTab(category) {
        // Validate category data
        if (!category || !category.name || !category.slug) {
            throw new Error('Invalid category data provided');
        }

        // Validate slug is CSS-safe
        if (!this.isValidCSSSelector(category.slug)) {
            console.warn(`Invalid slug generated for category ${category.name}: ${category.slug}`);
            category.slug = this.createValidSlug(category.name);
        }

        const li = document.createElement('li');
        li.className = 'nav-item me-1';
        li.setAttribute('data-dynamic', 'true'); // Mark as dynamically created
        
        const tabId = `${category.slug}-categories`;
        
        // Double-check the ID is valid
        if (!this.isValidCSSSelector(tabId)) {
            throw new Error(`Invalid tab ID generated: ${tabId}`);
        }
        
        li.innerHTML = `
            <a class="nav-link text-nowrap cursor-pointer"
               id="${tabId}-tab"
               data-bs-toggle="pill"
               data-bs-target="#${tabId}"
               role="tab"
               aria-controls="${tabId}"
               aria-selected="false">
                ${this.sanitizeHTML(category.name)}
            </a>
        `;

        // Create corresponding tab pane
        this.createCategoryTabPane(category);

        return li;
    }

    /**
     * Validate if a string is a valid CSS selector
     */
    isValidCSSSelector(selector) {
        if (!selector || typeof selector !== 'string') return false;
        
        try {
            // Try to use the selector in a querySelector call
            document.querySelector(`#${selector}`);
            return true;
        } catch (e) {
            return false;
        }
    }

    /**
     * Create tab pane for category
     */
    createCategoryTabPane(category) {
        const tabContent = document.querySelector('.tab-content');
        const tabId = `${category.slug}-categories`;
        
        // Check if pane already exists
        let existingPane = document.getElementById(tabId);
        if (existingPane) return;

        // Validate tab ID before creating
        if (!this.isValidCSSSelector(tabId)) {
            console.error(`Cannot create tab pane with invalid ID: ${tabId}`);
            return;
        }

        const pane = document.createElement('div');
        pane.className = 'tab-pane fade';
        pane.id = tabId;
        pane.setAttribute('role', 'tabpanel');
        pane.setAttribute('aria-labelledby', `${tabId}-tab`);
        pane.setAttribute('data-dynamic', 'true'); // Mark as dynamically created
        
        pane.innerHTML = `
            <div class="row row-cols-1 row-cols-lg-2 g-4 pb-5">
                <!-- Products will be loaded here -->
            </div>
        `;

        tabContent.appendChild(pane);
    }

    /**
     * Load fashion services for the top section
     */
    async loadFashionServices() {
        try {
            // This could be a separate endpoint or derived from categories
            const response = await fetch(`${this.baseURL}/services/fashion`);
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.services) {
                    this.renderFashionServices(data.services);
                }
            }
        } catch (error) {
            console.warn('Fashion services not available:', error);
            // Continue without fashion services
        }
    }

    /**
     * Render fashion services in the top section
     */
    renderFashionServices(services) {
        const servicesContainer = document.querySelector('.simplebar-content .row');
        if (!servicesContainer) return;

        servicesContainer.innerHTML = '';
        
        services.forEach(service => {
            const serviceCard = this.createServiceCard(service);
            servicesContainer.appendChild(serviceCard);
        });
    }

    /**
     * Create service card element
     */
    createServiceCard(service) {
        const col = document.createElement('div');
        col.className = 'col col-md-4 col-lg-3 col-xl-2 mb-4';
        
        col.innerHTML = `
            <div class="category-card w-100 text-center px-1 px-lg-2 px-xxl-3 mx-auto"
                 style="min-width: 165px"
                 data-service-id="${service.id}"
                 data-service-name="${service.name}">
                <div class="category-card-body">
                    <a class="d-block text-decoration-none" href="#" onclick="return false;">
                        <div class="bg-body-tertiary rounded-pill mb-3 mx-auto"
                             style="max-width: 164px">
                            <div class="ratio ratio-1x1">
                                <img src="${service.image || service.image_url || 'static/img/fashion/placeholder.jpg'}"
                                     class="rounded-pill"
                                     alt="${service.name}"
                                     onerror="this.src='static/img/fashion/placeholder.jpg'">
                            </div>
                        </div>
                        <h3 class="category-card-title h6 text-truncate">
                            ${this.sanitizeHTML(service.name)}
                        </h3>
                    </a>
                </div>
            </div>
        `;

        return col;
    }

    /**
     * Load products with proper category filtering
     */
    
    async loadProducts(categorySlug = 'all') {
        if (this.loading) return;
        
        this.loading = true;
        this.showLoadingState(categorySlug);

        try {
            let url = `${this.baseURL}/products?page_size=20`;
            
            // Add category filter if not 'all'
            if (categorySlug !== 'all' && this.categories[categorySlug]) {
                const category = this.categories[categorySlug];
                if (category.id) {
                    url += `&category_id=${category.id}`;
                } else if (category.name) {
                    url += `&category=${encodeURIComponent(category.name)}`;
                }
            }

            const response = await fetch(url);
            const data = await response.json();
            console.log(`CAT DATA - ${JSON.stringify(data)}`);

            if (data.success) {
                const products = data.products || data.data || [];
                this.updateCategoryProducts(categorySlug, products);
                this.renderProducts(categorySlug, products);
            } else {
                throw new Error(data.message || 'Failed to load products');
            }
        } catch (error) {
            console.error('Error loading products:', error);
            // this.showError(`Failed to load ${categorySlug} products`);
            this.renderEmptyState(categorySlug);
        } finally {
            this.loading = false;
        }
    }
        /*
    async loadProducts(categorySlug = 'all') {
    if (this.loading) return;
    this.loading = true;
    this.showLoadingState(categorySlug);

    try {
        let url;

        if (categorySlug === 'all') {
            url = `${this.baseURL}/products?page_size=20`;
        } else {
            // 👇 use your slug-based backend route
            url = `${this.baseURL}/products/${categorySlug}/category?page_size=20`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            const products = data.products || data.data || [];
            this.updateCategoryProducts(categorySlug, products);
            this.renderProducts(categorySlug, products);
        } else {
            throw new Error(data.message || 'Failed to load products');
        }
    } catch (error) {
        console.error('Error loading products:', error);
        this.showError(`Failed to load ${categorySlug} products`);
        this.renderEmptyState(categorySlug);
    } finally {
        this.loading = false;
    }
}*/


    /**
     * Update products in category cache
     */
    updateCategoryProducts(categorySlug, products) {
        if (this.categories[categorySlug]) {
            this.categories[categorySlug].products = products;
        }
    }

    /**
     * Handle category tab switching
     */
    async handleCategorySwitch(targetId) {
        const categorySlugMap = {
            '#all-categories': 'all',
            '#women-categories': 'women',
            '#men-categories': 'men',
            '#children-categories': 'children'
        };

        // Handle dynamic categories
        let categorySlug = categorySlugMap[targetId];
        if (!categorySlug) {
            // Extract slug from target ID for dynamic categories
            const match = targetId.match(/#(.+)-categories$/);
            if (match) {
                categorySlug = match[1];
            }
        }

        if (categorySlug && categorySlug !== this.currentCategory) {
            this.currentCategory = categorySlug;
            
            // Load products for this category if not cached
            if (!this.categories[categorySlug]?.products?.length) {
                await this.loadProducts(categorySlug);
            } else {
                // Use cached data
                this.renderProducts(categorySlug, this.categories[categorySlug].products);
            }
        }
    }

    /**
     * Render products in specific category tab
     */
    renderProducts(categorySlug, products) {
        const tabId = categorySlug === 'all' ? 'all-categories' : `${categorySlug}-categories`;
        const tabPane = document.getElementById(tabId);
        const container = tabPane?.querySelector('.row');
        
        if (!container) {
            console.error(`Container not found for category: ${categorySlug}`);
            return;
        }

        container.innerHTML = '';

        if (!products || products.length === 0) {
            this.renderEmptyState(categorySlug);
            return;
        }

        products.forEach(product => {
            const productCard = this.createProductCard(product);
            container.appendChild(productCard);
        });
    }

    /**
     * Render initial tabs with all categories
     */
    async renderInitialTabs() {
        // Load products for all visible categories
        const visibleCategories = Object.keys(this.categories).filter(key => 
            this.categories[key].id || key === 'all'
        );

        for (const categorySlug of visibleCategories) {
            if (categorySlug !== 'all') {
                await this.loadProducts(categorySlug);
            }
        }
    }

    /**
     * Create enhanced product card with proper category information
     */
    createProductCard(product) {
        const col = document.createElement('div');
        col.className = 'col';

        const primaryImage = this.getProductImage(product);
        const price = this.formatPrice(product.price);
        const categoryDisplay = this.getProductCategoryDisplay(product);
        const rating = this.calculateProductRating(product);
        const availability = this.getProductAvailability(product);

        col.innerHTML = `
            <article class="card hover-effect-scale bg-transparent overflow-hidden">
                <div class="row h-100 g-0">
                    <div class="col-sm-4 position-relative bg-body-tertiary overflow-hidden" 
                         style="min-height: 178px">
                        <img src="${primaryImage}" 
                             class="hover-effect-target position-absolute top-0 start-0 w-100 h-100 object-fit-cover" 
                             alt="${this.sanitizeHTML(product.name)}"
                             onerror="this.src='static/img/fashion/placeholder.jpg'">
                        ${product.is_featured ? '<span class="badge bg-primary position-absolute top-0 end-0 m-2">Featured</span>' : ''}
                    </div>
                    <div class="col-sm-8 card-body d-flex flex-column align-items-start p-3 p-sm-4">
                        <h3 class="h6 mt-1 mt-sm-0 mb-2">
                            <a class="stretched-link hover-effect-underline" 
                               href="#" 
                               data-product-id="${product.id}">
                                ${this.sanitizeHTML(product.name)}
                            </a>
                        </h3>
                        <div class="d-flex align-items-center gap-3 mb-3">
                            <div class="d-flex align-items-center gap-1">
                                <i class="fi-star-filled text-warning"></i>
                                <span class="fs-sm text-secondary-emphasis">${rating}</span>
                            </div>
                            <div class="fs-sm text-dark-emphasis">${categoryDisplay}</div>
                        </div>
                        ${product.description ? `
                            <p class="fs-sm text-muted mb-3 line-clamp-2">
                                ${this.sanitizeHTML(product.description.substring(0, 100))}${product.description.length > 100 ? '...' : ''}
                            </p>
                        ` : ''}
                        <div class="d-flex gap-2 mt-auto w-100">
                            <a href="#" 
                                    class="btn btn-outline-dark flex-grow-1"
                                    onclick="window.fashionAPI.viewProduct(${product.id})">
                                Contact For Details
                            </a>
                        </div>
                    </div>
                </div>
            </article>
        `;

        return col;
    }

    /**
     * Get product image with fallbacks
     */
    getProductImage(product) {
        return product.image_urls?.[0] || 
               product.images?.[0]?.file_path || 
               product.image || 
               'static/img/fashion/placeholder.jpg';
    }

    /**
     * Format product price
     */
    formatPrice(price) {
        if (!price) return 'Price on request';
        const numPrice = parseFloat(price);
        // return isNaN(numPrice) ? 'Price on request' : `₦ ${numPrice.toFixed(2)}`;
        return 'Price on request';
    }

    /**
     * Get product category display
     */
    getProductCategoryDisplay(product) {
        if (product.categories && product.categories.length > 0) {
            return product.categories[0].name;
        }
        if (product.category) {
            return typeof product.category === 'string' ? product.category : product.category.name;
        }
        return 'Fashion';
    }

    /**
     * Get product availability info
     */
    getProductAvailability(product) {

        /* const stock = product.stock || product.quantity || 0;
        
        if (stock <= 0) {
            return { available: false, message: 'Out of Stock', stock: 0 };
        }
        
        if (stock <= 5) {
            return { available: true, lowStock: true, stock: stock };
        }
        
        return { available: true, stock: stock }; */
        return { available: true, stock: 100 }; // Always available for demo
    }

    /**
     * Show loading state for specific category
     */
    showLoadingState(categorySlug) {
        const tabId = categorySlug === 'all' ? 'all-categories' : `${categorySlug}-categories`;
        const container = document.querySelector(`#${tabId} .row`);
        
        if (container) {
            container.innerHTML = `
                <div class="col-12">
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="text-muted">Loading ${categorySlug === 'all' ? 'all' : categorySlug} products...</p>
                    </div>
                </div>
            `;
        }
    }

    /**
     * Render empty state for specific category
     */
    renderEmptyState(categorySlug) {
        const tabId = categorySlug === 'all' ? 'all-categories' : `${categorySlug}-categories`;
        const container = document.querySelector(`#${tabId} .row`);
        
        if (container) {
            const categoryName = this.categories[categorySlug]?.name || categorySlug;
            container.innerHTML = `
                <div class="col-12">
                    <div class="text-center py-5">
                        <i class="fi-shopping-bag display-1 text-muted mb-3"></i>
                        <h4>No ${categoryName} Products Found</h4>
                        <p class="text-muted">Check back later or try browsing other categories.</p>
                        <button class="btn btn-primary" onclick="window.fashionAPI.loadProducts('${categorySlug}')">
                            <i class="fi-refresh me-2"></i>Refresh
                        </button>
                    </div>
                </div>
            `;
        }
    }

    /**
     * Handle service card clicks with category filtering
     */
    async handleServiceClick(serviceElement) {
        const serviceName = serviceElement.querySelector('.category-card-title')?.textContent?.trim();
        const serviceId = serviceElement.getAttribute('data-service-id');
        
        if (serviceName || serviceId) {
            try {
                let url = `${this.baseURL}/products?page_size=20`;
                if (serviceId) {
                    url += `&service_id=${serviceId}`;
                } else {
                    url += `&search=${encodeURIComponent(serviceName)}`;
                }

                const response = await fetch(url);
                const data = await response.json();
                
                if (data.success) {
                    const products = data.products || data.data || [];
                    this.showServiceResults(serviceName, products);
                }
            } catch (error) {
                console.error('Error filtering by service:', error);
                this.showError('Failed to filter products by service');
            }
        }
    }

    /**
     * Show service-filtered results
     */
    showServiceResults(serviceName, products) {
        // Switch to "All" tab and show service results
        const allTab = document.querySelector('#all-categories-tab');
        if (allTab) {
            const tab = new bootstrap.Tab(allTab);
            tab.show();
        }
        
        this.renderProducts('all', products);
        this.highlightActiveService(serviceName);
        
        // Show notification
        this.showInfo(`Showing results for "${serviceName}"`);
    }

    // ... (include all other methods from the original code: viewProduct, addToCart, showProductModal, etc.)

    /**
     * Calculate product rating
     */
    calculateProductRating(product) {
        if (product.rating) return parseFloat(product.rating).toFixed(1);
        if (product.reviews && product.reviews.length > 0) {
            const avg = product.reviews.reduce((sum, review) => sum + review.rating, 0) / product.reviews.length;
            return avg.toFixed(1);
        }
        return (Math.random() * 2 + 3).toFixed(1); // Fallback: 3.0-5.0
    }

    /**
     * Show info message
     */
    showInfo(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-info alert-dismissible fade show position-fixed top-0 end-0 m-3';
        alert.style.zIndex = '9999';
        alert.innerHTML = `
            <i class="fi-info-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);

        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 4000);
    }

    /**
     * Sanitize HTML to prevent XSS
     */
    sanitizeHTML(str) {
        if (!str) return '';
        const temp = document.createElement('div');
        temp.textContent = str;
        return temp.innerHTML;
    }

    // Additional utility methods...
    highlightActiveService(serviceName) {
        document.querySelectorAll('.category-card').forEach(card => {
            card.classList.remove('active');
            const title = card.querySelector('.category-card-title')?.textContent?.trim();
            if (title === serviceName) {
                card.classList.add('active');
            }
        });
    }

    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed top-0 end-0 m-3';
        alert.style.zIndex = '9999';
        alert.innerHTML = `
            <i class="fi-alert-triangle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);

        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

    showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 end-0 m-3';
        alert.style.zIndex = '9999';
        alert.innerHTML = `
            <i class="fi-check-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);

        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 3000);
    }

    /*
    // Placeholder methods for cart and product details
    async viewProduct(productId) {
        console.log('View product:', productId);
        // Implement product modal/page navigation
    }

    async addToCart(productId) {
        console.log('Add to cart:', productId);
        this.showSuccess('Product added to cart');
        // Implement cart functionality
    }

    */


    /**
 * Complete implementation of viewProduct method with professional product modal
 * Includes image gallery, product details, reviews, and purchase options
 */

/**
 * View product details in a comprehensive modal
 * @param {number|string} productId - The product ID to display
 */
async viewProduct(productId) {
    if (!productId) {
        this.showError('Invalid product ID');
        return;
    }

    try {
        // Show loading state
        this.showProductLoadingModal();
        
        // Fetch detailed product information
        const product = await this.fetchProductDetails(productId);
        
        if (!product) {
            this.showError('Product not found');
            this.hideProductModal();
            return;
        }

        // Show the complete product modal
        this.showProductModal(product);
        
    } catch (error) {
        console.error('Error viewing product:', error);
        // this.showError('Failed to load product details');
        this.hideProductModal();
    }
}

/**
 * Fetch detailed product information from backend
 * @param {number|string} productId - Product ID
 * @returns {Object|null} Product details or null if not found
 */
async fetchProductDetails(productId) {
    try {
        const response = await fetch(`${this.baseURL}/products/${productId}`);
        
        const data = await response.json();
        console.log(`PRODUCT DATA - ${JSON.stringify(data)}`);
        if (data.success && data.product) {
            return data.product;
        } else if (data.success && data) {
            return data;
        } else {
            throw new Error(data.message || 'Product not found');
        }
    } catch (error) {
        console.error('Error fetching product details:', error);
        return null;
    }
}

/**
 * Show loading modal while fetching product details
 */
showProductLoadingModal() {
    // Remove existing modal if any
    this.hideProductModal();
    
    const loadingModal = document.createElement('div');
    loadingModal.id = 'productModal';
    loadingModal.className = 'modal fade';
    loadingModal.setAttribute('tabindex', '-1');
    loadingModal.setAttribute('aria-labelledby', 'productModalLabel');
    loadingModal.setAttribute('aria-hidden', 'true');
    
    loadingModal.innerHTML = `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-body text-center py-5">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <h5>Loading product details...</h5>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(loadingModal);
    
    // Show the modal
    const modal = new bootstrap.Modal(loadingModal);
    modal.show();
}

/**
 * Show comprehensive product modal with all details
 * @param {Object} product - Complete product information
 */
showProductModal(product) {
    // Remove existing modal
    this.hideProductModal();
    
    const modal = document.createElement('div');
    modal.id = 'productModal';
    modal.className = 'modal fade';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('aria-labelledby', 'productModalLabel');
    modal.setAttribute('aria-hidden', 'true');
    
    modal.innerHTML = this.createProductModalHTML(product);
    document.body.appendChild(modal);
    
    // Initialize the modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    // Setup modal event listeners
    this.setupProductModalEvents(product, modal);
    
    // Initialize image gallery if multiple images
    this.initializeImageGallery(product);
    
    // Load related products
    this.loadRelatedProducts(product);
}

/**
 * Create comprehensive product modal HTML
 * @param {Object} product - Product data
 * @returns {string} Modal HTML
 */
createProductModalHTML(product) {
    const images = this.getProductImages(product);
    const price = this.formatPrice(product.price);
    const availability = this.getProductAvailability(product);
    const rating = this.calculateProductRating(product);
    const categoryDisplay = this.getProductCategoryDisplay(product);
    
    return `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header border-0 pb-0">
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body px-4 pt-0">
                    <div class="row g-4">
                        <!-- Product Images -->
                        <div class="col-lg-6">
                            ${this.createImageGalleryHTML(images, product.name)}
                        </div>
                        
                        <!-- Product Details -->
                        <div class="col-lg-6">
                            <div class="ps-lg-4">
                                <!-- Product Title & Rating -->
                                <div class="mb-3">
                                    <span class="badge bg-primary-subtle text-primary mb-2">${categoryDisplay}</span>
                                    <h1 class="h3 mb-2" id="productModalLabel">${this.sanitizeHTML(product.name)}</h1>
                                    <div class="d-flex align-items-center gap-3 mb-2">
                                        <div class="d-flex align-items-center gap-1">
                                            ${this.createStarRating(rating)}
                                            <span class="text-muted ms-1">(${product.reviews?.length || Math.floor(Math.random() * 50) + 10} reviews)</span>
                                        </div>
                                        ${product.is_featured ? '<span class="badge bg-warning text-dark">Featured</span>' : ''}
                                    </div>
                                </div>

                                <!-- Price & Availability -->
                                <div class="mb-4">
                                    <div class="d-flex align-items-center gap-3 mb-2">
                                        <span class="h4 text-primary mb-0">${price}</span>
                                        ${availability.available 
                                            ? `<span class="badge bg-success">In Stock</span>` 
                                            : `<span class="badge bg-danger">Out of Stock</span>`
                                        }
                                    </div>
                                    ${availability.lowStock ? '<small class="text-warning">Only few items left!</small>' : ''}
                                </div>

                                <!-- Product Description -->
                                ${product.description ? `
                                    <div class="mb-4">
                                        <h6>Description</h6>
                                        <p class="text-muted">${this.sanitizeHTML(product.description)}</p>
                                    </div>
                                ` : ''}

                                <!-- Product Attributes/Specifications -->
                                ${this.createProductAttributesHTML(product)}

                                <!-- Action Buttons -->
                                <div class="d-grid gap-2 d-md-flex">
                                    ${availability.available ? `
                                        <button class="btn btn-outline-dark" onclick="window.fashionAPI.contactForProduct(${product.id})">
                                        <i class="fi-whatsapp me-2"></i>Whatsapp
                                    </button>
                                    ` : `
                                        <button class="btn btn-outline-secondary flex-fill" disabled>
                                            <i class="fi-alert-circle me-2"></i>Out of Stock
                                        </button>
                                    `}
                                    <button class="btn btn-outline-dark" onclick="window.fashionAPI.contactForProduct(${product.id})">
                                        <i class="fi-phone me-2"></i>Call Us
                                    </button>
                                </div>

                                <!-- Additional Info -->
                                <div class="mt-4 pt-3 border-top">
                                    <div class="row g-3 text-center">
                                        <div class="col-4">
                                            <i class="fi-truck text-muted mb-2 d-block"></i>
                                            <small class="text-muted">Free Delivery</small>
                                        </div>
                                        <div class="col-4">
                                            <i class="fi-refresh-cw text-muted mb-2 d-block"></i>
                                            <small class="text-muted">Easy Returns</small>
                                        </div>
                                        <div class="col-4">
                                            <i class="fi-shield-check text-muted mb-2 d-block"></i>
                                            <small class="text-muted">Secure Payment</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Tabs for Reviews and Details -->
                    <div class="mt-5">
                        <ul class="nav nav-tabs" role="tablist">
                            <li class="nav-item">
                                <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#reviews-tab" role="tab">
                                    Reviews (${product.reviews?.length || Math.floor(Math.random() * 50) + 10})
                                </button>
                            </li>
                            <li class="nav-item">
                                <button class="nav-link" data-bs-toggle="tab" data-bs-target="#details-tab" role="tab">
                                    Details
                                </button>
                            </li>
                            <li class="nav-item">
                                <button class="nav-link" data-bs-toggle="tab" data-bs-target="#related-tab" role="tab">
                                    Related Products
                                </button>
                            </li>
                        </ul>
                        <div class="tab-content pt-4">
                            <div class="tab-pane fade show active" id="reviews-tab">
                                ${this.createReviewsHTML(product)}
                            </div>
                            <div class="tab-pane fade" id="details-tab">
                                ${this.createDetailedSpecsHTML(product)}
                            </div>
                            <div class="tab-pane fade" id="related-tab">
                                <div id="related-products-container">
                                    <div class="text-center py-3">
                                        <div class="spinner-border text-primary" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Get all product images with fallbacks
 * @param {Object} product - Product data
 * @returns {Array} Array of image URLs
 */
getProductImages(product) {
    const images = [];
    
    // Primary image sources
    if (product.image_urls && Array.isArray(product.image_urls)) {
        images.push(...product.image_urls);
    } else if (product.images && Array.isArray(product.images)) {
        images.push(...product.images.map(img => img.file_path || img.url));
    } else if (product.image) {
        images.push(product.image);
    }
    
    // Fallback if no images
    if (images.length === 0) {
        images.push('static/img/fashion/placeholder.jpg');
    }
    
    return images.filter(Boolean);
}

// /**
//  * Create image gallery HTML
//  * @param {Array} images - Array of image URLs
//  * @param {string} productName - Product name for alt text
//  * @returns {string} Image gallery HTML
//  */
// createImageGalleryHTML(images, productName) {
//     const mainImage = images[0];
    
//     return `
//         <div class="product-gallery">
//             <!-- Main Image -->
//             <div class="main-image-container mb-3">
//                 <img id="main-product-image" 
//                      src="${mainImage}" 
//                      class="img-fluid rounded" 
//                      alt="${this.sanitizeHTML(productName)}"
//                      style="width: 100%; height: 400px; object-fit: cover;"
//                      onerror="this.src='static/img/fashion/placeholder.jpg'">
//             </div>
            
//             <!-- Thumbnail Images -->
//             ${images.length > 1 ? `
//                 <div class="thumbnail-container">
//                     <div class="row g-2">
//                         ${images.map((image, index) => `
//                             <div class="col-3">
//                                 <img src="${image}" 
//                                      class="img-fluid rounded cursor-pointer thumbnail-image ${index === 0 ? 'active' : ''}"
//                                      style="width: 100%; height: 80px; object-fit: cover; border: 2px solid ${index === 0 ? '#0d6efd' : 'transparent'};"
//                                      onclick="window.fashionAPI.switchMainImage('${image}', this)"
//                                      alt="Product view ${index + 1}"
//                                      onerror="this.src='static/img/fashion/placeholder.jpg'">
//                             </div>
//                         `).join('')}
//                     </div>
//                 </div>
//             ` : ''}
//         </div>
//     `;
// }

// /**
//  * Switch main image in gallery
//  * @param {string} imageSrc - New image source
//  * @param {Element} thumbnailElement - Clicked thumbnail element
//  */
// switchMainImage(imageSrc, thumbnailElement) {
//     const mainImage = document.getElementById('main-product-image');
//     if (mainImage) {
//         mainImage.src = imageSrc;
//     }
    
//     // Update active thumbnail
//     document.querySelectorAll('.thumbnail-image').forEach(thumb => {
//         thumb.style.border = '2px solid transparent';
//         thumb.classList.remove('active');
//     });
    
//     if (thumbnailElement) {
//         thumbnailElement.style.border = '2px solid #0d6efd';
//         thumbnailElement.classList.add('active');
//     }
// }

// v2
/**
 * Create image gallery HTML
 * @param {Array} images - Array of image URLs
 * @param {string} productName - Product name for alt text
 * @returns {string} Image gallery HTML
 */
createImageGalleryHTML(images, productName) {
    const mainImage = images[0];

    return `
        <div class="product-gallery text-center">
            <!-- Main Image -->
            <div class="main-image-container mb-3" 
                 style="background-color: #f8f9fa; border-radius: 6px; overflow: hidden;">
                <img id="main-product-image" 
                     src="${mainImage}" 
                     class="img-fluid rounded"
                     alt="${this.sanitizeHTML(productName)}"
                     style="width: 100%; height: 400px; object-fit: contain; background-color: #fff;"
                     onerror="this.src='static/img/fashion/placeholder.jpg'">
            </div>

            <!-- Thumbnail Images -->
            ${images.length > 1 ? `
                <div class="thumbnail-container">
                    <div class="row g-2 justify-content-center">
                        ${images.map((image, index) => `
                            <div class="col-3 col-sm-2 col-md-2">
                                <div style="background-color: #f8f9fa; border-radius: 6px; overflow: hidden;">
                                    <img src="${image}" 
                                         class="img-fluid rounded cursor-pointer thumbnail-image ${index === 0 ? 'active' : ''}"
                                         style="width: 100%; height: 80px; object-fit: contain; background-color: #fff; border: 2px solid ${index === 0 ? '#0d6efd' : 'transparent'};"
                                         onclick="window.fashionAPI.switchMainImage('${image}', this)"
                                         alt="Product view ${index + 1}"
                                         onerror="this.src='static/img/fashion/placeholder.jpg'">
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

/**
 * Switch main image in gallery
 * @param {string} imageSrc - New image source
 * @param {Element} thumbnailElement - Clicked thumbnail element
 */
switchMainImage(imageSrc, thumbnailElement) {
    const mainImage = document.getElementById('main-product-image');
    if (mainImage) {
        mainImage.src = imageSrc;
    }

    // Update active thumbnail
    document.querySelectorAll('.thumbnail-image').forEach(thumb => {
        thumb.style.border = '2px solid transparent';
        thumb.classList.remove('active');
    });

    if (thumbnailElement) {
        thumbnailElement.style.border = '2px solid #0d6efd';
        thumbnailElement.classList.add('active');
    }
}


/**
 * Create star rating HTML
 * @param {number} rating - Rating value
 * @returns {string} Star rating HTML
 */
createStarRating(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 !== 0;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    let starsHTML = '';
    
    // Full stars
    for (let i = 0; i < fullStars; i++) {
        starsHTML += '<i class="fi-star-filled text-warning"></i>';
    }
    
    // Half star
    if (hasHalfStar) {
        starsHTML += '<i class="fi-star-half text-warning"></i>';
    }
    
    // Empty stars
    for (let i = 0; i < emptyStars; i++) {
        starsHTML += '<i class="fi-star text-muted"></i>';
    }
    
    starsHTML += `<span class="text-muted ms-1">${rating}</span>`;
    
    return starsHTML;
}

/**
 * Create product attributes HTML
 * @param {Object} product - Product data
 * @returns {string} Attributes HTML
 */
createProductAttributesHTML(product) {
    const attributes = [];
    
    // Common attributes
    if (product.brand) attributes.push(['Brand', product.brand]);
    if (product.material) attributes.push(['Material', product.material]);
    if (product.color) attributes.push(['Color', product.color]);
    if (product.size) attributes.push(['Size', product.size]);
    if (product.sku) attributes.push(['SKU', product.sku]);
    
    // Custom attributes from product.attributes
    if (product.attributes) {
        Object.entries(product.attributes).forEach(([key, value]) => {
            if (value) {
                attributes.push([key.charAt(0).toUpperCase() + key.slice(1), value]);
            }
        });
    }
    
    if (attributes.length === 0) return '';
    
    return `
        <div class="mb-4">
            <h6>Product Information</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    ${attributes.map(([key, value]) => `
                        <tr>
                            <td class="text-muted" style="width: 40%;">${key}:</td>
                            <td>${this.sanitizeHTML(value)}</td>
                        </tr>
                    `).join('')}
                </table>
            </div>
        </div>
    `;
}

/**
 * Create reviews HTML
 * @param {Object} product - Product data
 * @returns {string} Reviews HTML
 */
createReviewsHTML(product) {
    const reviews = product.reviews || this.generateMockReviews();
    
    return `
        <div class="reviews-container">
            <div class="row">
                <div class="col-lg-8">
                    ${reviews.map(review => `
                        <div class="border-bottom pb-3 mb-3">
                            <div class="d-flex align-items-center gap-3 mb-2">
                                <div class="d-flex align-items-center gap-1">
                                    ${this.createStarRating(review.rating)}
                                </div>
                                <strong>${this.sanitizeHTML(review.name || 'Anonymous')}</strong>
                                <small class="text-muted">${new Date(review.created_at || Date.now()).toLocaleDateString()}</small>
                            </div>
                            <p class="mb-0">${this.sanitizeHTML(review.comment || review.review || '')}</p>
                        </div>
                    `).join('')}
                    
                    <!-- Add Review Form -->
                    <div class="mt-4">
                        <h6>Write a Review</h6>
                        <form id="review-form" class="mt-3">
                            <div class="mb-3">
                                <label class="form-label">Rating</label>
                                <div class="rating-input">
                                    ${[5,4,3,2,1].map(star => `
                                        <input type="radio" name="rating" value="${star}" id="star${star}">
                                        <label for="star${star}"><i class="fi-star"></i></label>
                                    `).join('')}
                                </div>
                            </div>
                            <div class="mb-3">
                                <label for="review-name" class="form-label">Name</label>
                                <input type="text" class="form-control" id="review-name" required>
                            </div>
                            <div class="mb-3">
                                <label for="review-comment" class="form-label">Review</label>
                                <textarea class="form-control" id="review-comment" rows="3" required></textarea>
                            </div>
                            <button type="submit" class="btn btn-primary">Submit Review</button>
                        </form>
                    </div>
                </div>
                
                <!-- Review Summary -->
                <div class="col-lg-4">
                    <div class="bg-light p-3 rounded">
                        <h6>Review Summary</h6>
                        ${this.createReviewSummary(reviews)}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Create detailed specifications HTML
 * @param {Object} product - Product data
 * @returns {string} Specifications HTML
 */
createDetailedSpecsHTML(product) {
    return `
        <div class="specifications">
            <div class="row">
                <div class="col-lg-6">
                    <h6>Product Details</h6>
                    ${this.createProductAttributesHTML(product)}
                    
                    ${product.care_instructions ? `
                        <h6>Care Instructions</h6>
                        <p class="text-muted">${this.sanitizeHTML(product.care_instructions)}</p>
                    ` : ''}
                </div>
                <div class="col-lg-6">
                    <h6>Shipping & Returns</h6>
                    <ul class="list-unstyled">
                        <li class="mb-2"><i class="fi-truck text-primary me-2"></i>Free shipping on orders over $500</li>
                        <li class="mb-2"><i class="fi-refresh-cw text-primary me-2"></i>Quality Materials</li>
                        <li class="mb-2"><i class="fi-clock text-primary me-2"></i>Fast Service Delivery</li>
                    </ul>
                    
                    <h6>Size Guide</h6>
                    <p class="text-muted">Please refer to our size guide for accurate measurements.</p>
                    <button class="btn btn-outline-primary btn-sm" onclick="window.fashionAPI.showSizeGuide()">
                        View Size Guide
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Generate mock reviews if none exist
 * @returns {Array} Array of mock reviews
 */
generateMockReviews() {
    const mockReviews = [
        { name: 'Sarah Johnson', rating: 5, comment: 'Excellent quality and perfect fit. Highly recommended!', created_at: Date.now() - 86400000 },
        { name: 'Mike Chen', rating: 4, comment: 'Good product, fast delivery. Would buy again.', created_at: Date.now() - 172800000 },
        { name: 'Emma Wilson', rating: 5, comment: 'Beautiful design and great material. Love it!', created_at: Date.now() - 259200000 }
    ];
    
    return mockReviews.slice(0, Math.floor(Math.random() * 3) + 1);
}

/**
 * Create review summary HTML
 * @param {Array} reviews - Array of reviews
 * @returns {string} Review summary HTML
 */
createReviewSummary(reviews) {
    const totalReviews = reviews.length;
    const avgRating = reviews.reduce((sum, r) => sum + r.rating, 0) / totalReviews;
    const ratingCounts = [5,4,3,2,1].map(rating => 
        reviews.filter(r => r.rating === rating).length
    );
    
    return `
        <div class="text-center mb-3">
            <div class="display-6 mb-1">${avgRating.toFixed(1)}</div>
            <div class="mb-1">${this.createStarRating(avgRating)}</div>
            <small class="text-muted">${totalReviews} review${totalReviews !== 1 ? 's' : ''}</small>
        </div>
        
        <div class="rating-breakdown">
            ${ratingCounts.map((count, index) => {
                const rating = 5 - index;
                const percentage = totalReviews > 0 ? (count / totalReviews) * 100 : 0;
                return `
                    <div class="d-flex align-items-center gap-2 mb-1">
                        <small>${rating}</small>
                        <i class="fi-star-filled text-warning"></i>
                        <div class="progress flex-fill" style="height: 4px;">
                            <div class="progress-bar" style="width: ${percentage}%"></div>
                        </div>
                        <small>${count}</small>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

/**
 * Setup event listeners for product modal
 * @param {Object} product - Product data
 * @param {Element} modal - Modal element
 */
setupProductModalEvents(product, modal) {
    // Review form submission
    const reviewForm = modal.querySelector('#review-form');
    if (reviewForm) {
        reviewForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitReview(product.id, reviewForm);
        });
    }
    
    // Modal cleanup on hide
    modal.addEventListener('hidden.bs.modal', () => {
        modal.remove();
    });
}

/**
 * Load related products
 * @param {Object} product - Current product
 */
async loadRelatedProducts(product) {
    try {
        const category = product.categories?.[0]?.id || product.category?.id;
        let url = `${this.baseURL}/products?page_size=4&exclude=${product.id}`;
        
        if (category) {
            url += `&category_id=${category}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            const relatedProducts = data.products || data.data || [];
            this.renderRelatedProducts(relatedProducts);
        }
    } catch (error) {
        console.error('Error loading related products:', error);
        this.renderEmptyRelatedProducts();
    }
}

/**
 * Render related products in modal
 * @param {Array} products - Related products
 */
renderRelatedProducts(products) {
    const container = document.getElementById('related-products-container');
    if (!container) return;
    
    if (products.length === 0) {
        this.renderEmptyRelatedProducts();
        return;
    }
    
    container.innerHTML = `
        <div class="row g-3">
            ${products.map(product => `
                <div class="col-md-6 col-lg-3">
                    <div class="card h-100">
                        <img src="${this.getProductImage(product)}" 
                             class="card-img-top" 
                             style="height: 200px; object-fit: cover;"
                             alt="${this.sanitizeHTML(product.name)}"
                             onerror="this.src='static/img/fashion/placeholder.jpg'">
                        <div class="card-body d-flex flex-column">
                            <h6 class="card-title">${this.sanitizeHTML(product.name)}</h6>
                            <p class="card-text text-muted small flex-grow-1">${this.sanitizeHTML((product.description || '').substring(0, 80))}...</p>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="text-primary fw-bold">${this.formatPrice(product.price)}</span>
                                <button class="btn btn-sm btn-outline-primary" 
                                        onclick="window.fashionAPI.viewProduct(${product.id})">
                                    View
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

/**
 * Render empty related products state
 */
renderEmptyRelatedProducts() {
    const container = document.getElementById('related-products-container');
    if (!container) return;
    
    container.innerHTML = `
        <div class="text-center text-muted">
            <i class="fi-shopping-bag display-6 mb-3"></i>
            <p>No related products found.</p>
        </div>
    `;
}

/**
 * Submit product review
 * @param {number} productId - Product ID
 * @param {Element} form - Review form element
 */
async submitReview(productId, form) {
    const formData = new FormData(form);
    const reviewData = {
        product_id: productId,
        name: formData.get('review-name'),
        rating: parseInt(formData.get('rating')),
        comment: formData.get('review-comment')
    };
    
    if (!reviewData.rating) {
        this.showError('Please select a rating');
        return;
    }
    
    try {
        const response = await fetch(`${this.baseURL}/reviews`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(reviewData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            this.showSuccess('Review submitted successfully!');
            form.reset();
            // Refresh the product modal to show new review
            setTimeout(() => {
                this.viewProduct(productId);
            }, 1000);
        } else {
            throw new Error(data.message || 'Failed to submit review');
        }
    } catch (error) {
        console.error('Error submitting review:', error);
        this.showError('Failed to submit review');
    }
}

/**
 * Hide product modal
 */
hideProductModal() {
    const existingModal = document.getElementById('productModal');
    if (existingModal) {
        const modal = bootstrap.Modal.getInstance(existingModal);
        if (modal) {
            modal.hide();
        }
        existingModal.remove();
    }
}

/**
 * Contact for product (placeholder implementation)
 * @param {number} productId - Product ID
 */
async contactForProduct(productId) {
    // This could open a contact form, WhatsApp, or phone call
    const product = await this.fetchProductDetails(productId);
    const message = `Hi, I'm interested in ${product?.name || 'this product'}. Can you provide more details?`;
    
    const whatsappNumber = '+2348025922093'; 
    const whatsappUrl = `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(message)}`;
    
    window.open(whatsappUrl, '_blank');
}

/**
 * Buy now functionality (placeholder implementation)
 * @param {number} productId - Product ID
 */
async buyNow(productId) {
    // Add to cart and redirect to checkout
    await this.addToCart(productId);
    
    // Redirect to checkout page or show checkout modal
    this.showSuccess('Redirecting to checkout...');
    
    // Example: Redirect to checkout
    // window.location.href = '/checkout';
}

/**
 * Show size guide modal
 */
showSizeGuide() {
    // Implementation for size guide modal
    this.showInfo('Connect with SimplyLovey Fashion On Whatsapp kindly for our various sizes and guides on how to choose the best.');
}


/**
 * Enhanced addToCart method with quantity and options
 * @param {number} productId - Product ID
 * @param {number} quantity - Quantity to add (default: 1)
 * @param {Object} options - Product options (size, color, etc.)
 */
async addToCart(productId, quantity = 1, options = {}) {
    if (!productId) {
        this.showError('Invalid product ID');
        return;
    }

    try {
        // Get product details first to validate
        const product = await this.fetchProductDetails(productId);
        
        if (!product) {
            this.showError('Product not found');
            return;
        }
        
        // Check availability
        // comment so it won't show out of stock
        
        const availability = this.getProductAvailability(product);
        if (!availability.available) {
            this.showError('Product is out of stock');
            return;
        }

        // Prepare cart item data
        const cartItem = {
            product_id: productId,
            quantity: quantity,
            options: options,
            price: product.price
        };

        // Send to backend cart API
        const response = await fetch(`${this.baseURL}/cart/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Add authentication headers if needed
                // 'Authorization': `Bearer ${this.getAuthToken()}`
            },
            body: JSON.stringify(cartItem)
        });

        const data = await response.json();

        if (data.success) {
            this.showSuccess(`${product.name} added to cart!`);
            this.updateCartCounter();
            this.showMiniCart(product, quantity);
        } else {
            throw new Error(data.message || 'Failed to add to cart');
        }

    } catch (error) {
        console.error('Error adding to cart:', error);
        this.showError('Failed to add product to cart');
    }
}

/**
 * Show mini cart popup after adding item
 * @param {Object} product - Product that was added
 * @param {number} quantity - Quantity added
 */
showMiniCart(product, quantity) {
    // Remove existing mini cart
    const existingMiniCart = document.getElementById('miniCart');
    if (existingMiniCart) {
        existingMiniCart.remove();
    }

    const miniCart = document.createElement('div');
    miniCart.id = 'miniCart';
    miniCart.className = 'position-fixed top-0 end-0 m-3 bg-white border rounded shadow-lg p-3';
    miniCart.style.cssText = `
        z-index: 9999;
        width: 300px;
        animation: slideInRight 0.3s ease-out;
    `;

    miniCart.innerHTML = `
        <div class="d-flex align-items-center gap-3 mb-3">
            <i class="fi-check-circle text-success"></i>
            <h6 class="mb-0">Added to Cart</h6>
            <button type="button" class="btn-close ms-auto" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
        <div class="d-flex gap-3 mb-3">
            <img src="${this.getProductImage(product)}" 
                 class="rounded" 
                 style="width: 60px; height: 60px; object-fit: cover;"
                 alt="${this.sanitizeHTML(product.name)}">
            <div class="flex-grow-1">
                <h6 class="mb-1">${this.sanitizeHTML(product.name)}</h6>
                <p class="text-muted small mb-1">Qty: ${quantity}</p>
                <p class="text-primary fw-bold mb-0">${this.formatPrice(product.price)}</p>
            </div>
        </div>
        <div class="d-grid gap-2">
            <button class="btn btn-primary btn-sm" onclick="window.fashionAPI.viewCart()">
                View Cart
            </button>
            <button class="btn btn-outline-primary btn-sm" onclick="window.fashionAPI.continueShopping()">
                Continue Shopping
            </button>
        </div>
    `;

    document.body.appendChild(miniCart);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (miniCart.parentNode) {
            miniCart.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => miniCart.remove(), 300);
        }
    }, 5000);
}

/**
 * Update cart counter in header
 */
async updateCartCounter() {
    try {
        const response = await fetch(`${this.baseURL}/cart/count`);
        const data = await response.json();
        
        if (data.success) {
            const cartCounters = document.querySelectorAll('.cart-counter, [data-cart-count]');
            cartCounters.forEach(counter => {
                counter.textContent = data.count || 0;
                counter.style.display = data.count > 0 ? 'inline' : 'none';
            });
        }
    } catch (error) {
        console.error('Error updating cart counter:', error);
    }
}

/**
 * View cart page/modal
 */
viewCart() {
    // Close mini cart
    const miniCart = document.getElementById('miniCart');
    if (miniCart) miniCart.remove();
    
    // Navigate to cart page or show cart modal
    window.location.href = '/cart';
    // OR show cart modal: this.showCartModal();
}

/**
 * Continue shopping - close mini cart and return to products
 */
continuesShopping() {
    const miniCart = document.getElementById('miniCart');
    if (miniCart) miniCart.remove();
}

/**
 * Show comprehensive cart modal
 */
async showCartModal() {
    try {
        const response = await fetch(`${this.baseURL}/cart`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load cart');
        }

        const cartItems = data.items || [];
        this.renderCartModal(cartItems);
        
    } catch (error) {
        console.error('Error loading cart:', error);
        this.showError('Failed to load cart');
    }
}

/**
 * Render cart modal with items
 * @param {Array} cartItems - Array of cart items
 */
renderCartModal(cartItems) {
    const modal = document.createElement('div');
    modal.id = 'cartModal';
    modal.className = 'modal fade';
    modal.setAttribute('tabindex', '-1');
    
    const total = cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Shopping Cart (${cartItems.length} items)</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    ${cartItems.length === 0 ? `
                        <div class="text-center py-5">
                            <i class="fi-shopping-cart display-1 text-muted mb-3"></i>
                            <h5>Your cart is empty</h5>
                            <p class="text-muted">Start shopping to add items to your cart</p>
                            <button class="btn btn-primary" data-bs-dismiss="modal">Continue Shopping</button>
                        </div>
                    ` : `
                        <div class="cart-items">
                            ${cartItems.map(item => this.createCartItemHTML(item)).join('')}
                        </div>
                        <div class="border-top pt-3 mt-3">
                            <div class="d-flex justify-content-between align-items-center">
                                <h5>Total: ${this.formatPrice(total)}</h5>
                                <div class="gap-2 d-flex">
                                    <button class="btn btn-outline-primary" data-bs-dismiss="modal">Continue Shopping</button>
                                    <button class="btn btn-primary" onclick="window.fashionAPI.proceedToCheckout()">
                                        Proceed to Checkout
                                    </button>
                                </div>
                            </div>
                        </div>
                    `}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    modal.addEventListener('hidden.bs.modal', () => {
        modal.remove();
    });
}

/**
 * Create cart item HTML
 * @param {Object} item - Cart item
 * @returns {string} Cart item HTML
 */
createCartItemHTML(item) {
    return `
        <div class="cart-item d-flex gap-3 border-bottom pb-3 mb-3" data-item-id="${item.id}">
            <img src="${item.product?.image || this.getProductImage(item.product) || 'static/img/fashion/placeholder.jpg'}" 
                 class="rounded" 
                 style="width: 80px; height: 80px; object-fit: cover;"
                 alt="${this.sanitizeHTML(item.product?.name || 'Product')}">
            <div class="flex-grow-1">
                <h6 class="mb-1">${this.sanitizeHTML(item.product?.name || 'Product')}</h6>
                <p class="text-muted small mb-2">${this.formatPrice(item.price)} each</p>
                <div class="d-flex align-items-center gap-2">
                    <div class="input-group" style="width: 120px;">
                        <button class="btn btn-outline-secondary btn-sm" onclick="window.fashionAPI.updateCartQuantity(${item.id}, ${item.quantity - 1})">-</button>
                        <input type="number" class="form-control form-control-sm text-center" value="${item.quantity}" min="1" onchange="window.fashionAPI.updateCartQuantity(${item.id}, this.value)">
                        <button class="btn btn-outline-secondary btn-sm" onclick="window.fashionAPI.updateCartQuantity(${item.id}, ${item.quantity + 1})">+</button>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="window.fashionAPI.removeFromCart(${item.id})">
                        <i class="fi-trash"></i>
                    </button>
                </div>
            </div>
            <div class="text-end">
                <p class="fw-bold mb-0">${this.formatPrice(item.price * item.quantity)}</p>
            </div>
        </div>
    `;
}

/**
 * Update cart item quantity
 * @param {number} itemId - Cart item ID
 * @param {number} newQuantity - New quantity
 */
async updateCartQuantity(itemId, newQuantity) {
    if (newQuantity < 1) {
        this.removeFromCart(itemId);
        return;
    }

    try {
        const response = await fetch(`${this.baseURL}/cart/${itemId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quantity: parseInt(newQuantity) })
        });

        const data = await response.json();

        if (data.success) {
            this.showSuccess('Cart updated');
            this.updateCartCounter();
            // Refresh cart modal if open
            const cartModal = document.getElementById('cartModal');
            if (cartModal) {
                this.showCartModal();
            }
        } else {
            throw new Error(data.message || 'Failed to update cart');
        }
    } catch (error) {
        console.error('Error updating cart:', error);
        this.showError('Failed to update cart');
    }
}

/**
 * Remove item from cart
 * @param {number} itemId - Cart item ID
 */
async removeFromCart(itemId) {
    try {
        const response = await fetch(`${this.baseURL}/cart/${itemId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            this.showSuccess('Item removed from cart');
            this.updateCartCounter();
            
            // Remove item from UI
            const itemElement = document.querySelector(`[data-item-id="${itemId}"]`);
            if (itemElement) {
                itemElement.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => {
                    itemElement.remove();
                    // Refresh cart if empty
                    const remainingItems = document.querySelectorAll('.cart-item');
                    if (remainingItems.length === 0) {
                        this.showCartModal();
                    }
                }, 300);
            }
        } else {
            throw new Error(data.message || 'Failed to remove item');
        }
    } catch (error) {
        console.error('Error removing from cart:', error);
        this.showError('Failed to remove item from cart');
    }
}

/**
 * Proceed to checkout
 */
proceedToCheckout() {
    // Close cart modal
    const cartModal = document.getElementById('cartModal');
    if (cartModal) {
        const modal = bootstrap.Modal.getInstance(cartModal);
        if (modal) modal.hide();
    }
    
    // Navigate to checkout
    window.location.href = '/checkout';
}

/**
 * Initialize image gallery interactions
 * @param {Object} product - Product data
 */
initializeImageGallery(product) {
    const images = this.getProductImages(product);
    
    if (images.length <= 1) return;
    
    // Add keyboard navigation
    document.addEventListener('keydown', (e) => {
        const modal = document.getElementById('productModal');
        if (!modal || !modal.classList.contains('show')) return;
        
        const activeThumb = document.querySelector('.thumbnail-image.active');
        if (!activeThumb) return;
        
        const thumbnails = Array.from(document.querySelectorAll('.thumbnail-image'));
        const currentIndex = thumbnails.indexOf(activeThumb);
        
        if (e.key === 'ArrowRight' && currentIndex < thumbnails.length - 1) {
            thumbnails[currentIndex + 1].click();
        } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
            thumbnails[currentIndex - 1].click();
        }
    });
    
    // Add touch/swipe support for mobile
    this.addSwipeSupport();
}

/**
 * Add swipe support for image gallery on mobile
 */
addSwipeSupport() {
    const mainImage = document.getElementById('main-product-image');
    if (!mainImage) return;
    
    let startX = 0;
    let startY = 0;
    
    mainImage.addEventListener('touchstart', (e) => {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
    });
    
    mainImage.addEventListener('touchend', (e) => {
        const endX = e.changedTouches[0].clientX;
        const endY = e.changedTouches[0].clientY;
        
        const diffX = startX - endX;
        const diffY = startY - endY;
        
        // Only handle horizontal swipes
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
            const thumbnails = Array.from(document.querySelectorAll('.thumbnail-image'));
            const activeThumb = document.querySelector('.thumbnail-image.active');
            const currentIndex = thumbnails.indexOf(activeThumb);
            
            if (diffX > 0 && currentIndex < thumbnails.length - 1) {
                // Swipe left - next image
                thumbnails[currentIndex + 1].click();
            } else if (diffX < 0 && currentIndex > 0) {
                // Swipe right - previous image
                thumbnails[currentIndex - 1].click();
            }
        }
    });
}

/**
 * Add CSS animations for enhanced UX
 */
addModalAnimations() {
    // Add CSS for animations if not already present
    if (!document.getElementById('modal-animations')) {
        const style = document.createElement('style');
        style.id = 'modal-animations';
        style.textContent = `
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            
            @keyframes slideOutRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
            
            @keyframes fadeOut {
                from { opacity: 1; transform: scale(1); }
                to { opacity: 0; transform: scale(0.9); }
            }
            
            .hover-effect-scale:hover .hover-effect-target {
                transform: scale(1.05);
                transition: transform 0.3s ease;
            }
            
            .hover-effect-underline:hover {
                text-decoration: underline !important;
            }
            
            .line-clamp-2 {
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            
            .cursor-pointer {
                cursor: pointer;
            }
            
            .rating-input {
                display: flex;
                flex-direction: row-reverse;
                gap: 5px;
            }
            
            .rating-input input {
                display: none;
            }
            
            .rating-input label {
                cursor: pointer;
                font-size: 1.2em;
                color: #ddd;
            }
            
            .rating-input label:hover,
            .rating-input label:hover ~ label,
            .rating-input input:checked ~ label {
                color: #ffc107;
            }
        `;
        document.head.appendChild(style);
    }
}

}


// Initialize the Fashion Products API
const fashionAPI = new FashionProductsAPI(apiURL);

// Initialize animations when class is instantiated
(() => {
    if (typeof fashionAPI !== 'undefined') {
        fashionAPI.addModalAnimations();
    }
})();

// Make it globally available
window.fashionAPI = fashionAPI;

// Expose methods globally for onclick handlers
window.viewProduct = (id) => fashionAPI.viewProduct(id);
window.addToCart = (id) => fashionAPI.addToCart(id);

// new
// Make new methods globally available
window.switchMainImage = (imageSrc, thumbnailElement) => fashionAPI.switchMainImage(imageSrc, thumbnailElement);
window.contactForProduct = (id) => fashionAPI.contactForProduct(id);
window.buyNow = (id) => fashionAPI.buyNow(id);
window.showSizeGuide = () => fashionAPI.showSizeGuide();
