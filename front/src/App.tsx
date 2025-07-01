import React, { useState } from 'react';
import { CartProvider } from './context/CartContext';
import { CategorySlider } from './components/CategorySlider';
import { ProductCard } from './components/ProductCard';
import { ProductDetail } from './components/ProductDetail';
import { Cart } from './components/Cart';
import { Checkout } from './components/Checkout';
import { OrderSuccess } from './components/OrderSuccess';
import { MyOrders } from './components/MyOrders';
import { BottomNav } from './components/BottomNav';
import { categories, products } from './data/mockData';
import { Product } from './types';

type Page = 'home' | 'product' | 'cart' | 'checkout' | 'success' | 'orders';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('home');
  const [selectedCategory, setSelectedCategory] = useState(categories[0].id);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  const filteredProducts = products.filter(product => product.categoryId === selectedCategory);

  const handleProductClick = (product: Product) => {
    setSelectedProduct(product);
    setCurrentPage('product');
  };

  const handleNavigation = (page: string) => {
    setCurrentPage(page as Page);
  };

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'home':
        return (
          <div className="min-h-screen bg-mandarin-bg pb-20">
            {/* Header */}
            <div className="bg-gradient-to-r from-mandarin-orange to-yellow-500 text-white px-6 py-8 rounded-b-3xl">
              <div className="flex items-center space-x-3 mb-2">
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                  <span className="text-2xl">🍊</span>
                </div>
                <div>
                  <h1 className="text-2xl font-bold">Мандарин</h1>
                  <p className="text-orange-100 text-sm">Доставка еды</p>
                </div>
              </div>
              <p className="text-orange-100 mt-1">Быстро и вкусно</p>
            </div>

            {/* Category Slider */}
            <CategorySlider
              categories={categories}
              selectedCategory={selectedCategory}
              onCategorySelect={setSelectedCategory}
            />

            {/* Products Grid */}
            <div className="px-4 pb-4">
              <h2 className="text-xl font-bold text-white mb-4">
                {categories.find(c => c.id === selectedCategory)?.name}
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {filteredProducts.map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    onProductClick={handleProductClick}
                  />
                ))}
              </div>
            </div>
          </div>
        );

      case 'product':
        return selectedProduct ? (
          <ProductDetail
            product={selectedProduct}
            onBack={() => setCurrentPage('home')}
          />
        ) : null;

      case 'cart':
        return (
          <Cart
            onBack={() => setCurrentPage('home')}
            onCheckout={() => setCurrentPage('checkout')}
          />
        );

      case 'checkout':
        return (
          <Checkout
            onBack={() => setCurrentPage('cart')}
            onOrderComplete={() => setCurrentPage('success')}
          />
        );

      case 'success':
        return (
          <OrderSuccess
            onBackToHome={() => setCurrentPage('home')}
          />
        );

      case 'orders':
        return (
          <MyOrders
            onBack={() => setCurrentPage('home')}
          />
        );

      default:
        return null;
    }
  };

  const showBottomNav = ['home', 'cart', 'orders'].includes(currentPage);

  return (
    <CartProvider>
      <div className="relative">
        {renderCurrentPage()}
        {showBottomNav && (
          <BottomNav
            currentPage={currentPage}
            onNavigate={handleNavigation}
          />
        )}
      </div>
    </CartProvider>
  );
}

export default App;