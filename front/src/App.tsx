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
import { Phone } from 'lucide-react';
import { useGetCategoriesQuery, useGetProductsQuery } from './store/api';
import { mapApiCategoryToCategory, mapApiProductToProduct } from './utils/mappers';
import { Product } from './types';
import {LoadingSpinner} from "./shared/ui/LoadingSpinner.tsx";
import {ErrorMessage} from "./shared/ui/ErrorMessage.tsx";

type Page = 'home' | 'product' | 'wok-builder' | 'cart' | 'checkout' | 'success' | 'orders';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('home');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  // Загружаем категории
  const { 
    data: apiCategories, 
    isLoading: categoriesLoading, 
    error: categoriesError 
  } = useGetCategoriesQuery();

  // Загружаем продукты для выбранной категории
  const { 
    data: apiProducts, 
    isLoading: productsLoading, 
    error: productsError 
  } = useGetProductsQuery(
    { categoryId: selectedCategory },
    { skip: !selectedCategory }
  );

  // Маппим данные из API
  const categories = apiCategories ? apiCategories.map(mapApiCategoryToCategory) : [];
  const products = apiProducts ? apiProducts.map(mapApiProductToProduct) : [];

  // Устанавливаем первую категорию по умолчанию
  React.useEffect(() => {
    if (categories.length > 0 && !selectedCategory) {
      setSelectedCategory(categories[0].id);
    }
  }, [categories, selectedCategory]);

  const handleProductClick = (product: Product) => {
    setSelectedProduct(product);
    if (product.isCustomizable) {
      setCurrentPage('wok-builder');
    } else {
      setCurrentPage('product');
    }
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
            <div className="bg-mandarin-bg px-6 py-4 border-b border-gray-600">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <img 
                    src="/logo_orange.png" 
                    alt="Мандарин" 
                    className="w-16 h-16 object-contain"
                  />
                  <div>
                    <h1 className="text-lg font-bold text-white">Мандарин</h1>
                    <p className="text-gray-400 text-xs leading-relaxed">
                      Доставка ежедневно по Черноголовке и ближайшим населенным пунктам
                    </p>
                  </div>
                </div>
                <button className="bg-mandarin-card p-2 rounded-full hover:bg-mandarin-card-light transition-colors border border-gray-600">
                  <Phone size={20} className="text-mandarin-orange" />
                </button>
              </div>
            </div>

            {/* Category Slider */}
            {categoriesLoading ? (
              <div className="py-8">
                <LoadingSpinner />
              </div>
            ) : categoriesError ? (
              <ErrorMessage message="Ошибка загрузки категорий" />
            ) : (
              <CategorySlider
                categories={categories}
                selectedCategory={selectedCategory}
                onCategorySelect={setSelectedCategory}
              />
            )}

            {/* Products Grid */}
            <div className="px-4 pb-4">
              {selectedCategory && (
                <>
                  <h2 className="text-xl font-bold text-white mb-4">
                    {categories.find(c => c.id === selectedCategory)?.name}
                  </h2>
                  
                  {productsLoading ? (
                    <div className="py-8">
                      <LoadingSpinner />
                    </div>
                  ) : productsError ? (
                    <ErrorMessage message="Ошибка загрузки товаров" />
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {products.map((product) => (
                        <ProductCard
                          key={product.id}
                          product={product}
                          onProductClick={handleProductClick}
                        />
                      ))}
                    </div>
                  )}
                </>
              )}
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

      // case 'wok-builder':
      //   return selectedProduct ? (
      //     <WokBuilder
      //       product={selectedProduct}
      //       onBack={() => setCurrentPage('home')}
      //     />
      //   ) : null;

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