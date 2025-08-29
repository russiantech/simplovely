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
            this.showError(`Failed to load ${categorySlug} products`);
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
                        ${!availability.available ? `
                            <small class="text-danger mt-2">${availability.message}</small>
                        ` : availability.lowStock ? `
                            <small class="text-warning mt-2">Only ${availability.stock} left</small>
                        ` : ''}
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
        return isNaN(numPrice) ? 'Price on request' : `$${numPrice.toFixed(2)}`;
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
        const stock = product.stock || product.quantity || 0;
        
        if (stock <= 0) {
            return { available: false, message: 'Out of Stock', stock: 0 };
        }
        
        if (stock <= 5) {
            return { available: true, lowStock: true, stock: stock };
        }
        
        return { available: true, stock: stock };
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
}

// Initialize the Fashion Products API
const fashionAPI = new FashionProductsAPI(apiURL);

// Make it globally available
window.fashionAPI = fashionAPI;

// Expose methods globally for onclick handlers
window.viewProduct = (id) => fashionAPI.viewProduct(id);
window.addToCart = (id) => fashionAPI.addToCart(id);