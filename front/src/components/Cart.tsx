import React, { useState } from 'react';
import { ArrowLeft, Plus, Minus, Trash2, ShoppingBag, X } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { products } from '../data/mockData';

interface CartProps {
  onBack: () => void;
  onCheckout: () => void;
}

export const Cart: React.FC<CartProps> = ({ onBack, onCheckout }) => {
  const { state, updateQuantity, removeItem, addItem } = useCart();
  const [showRecommendations, setShowRecommendations] = useState(false);

  // Получаем все уникальные рекомендации из товаров в корзине
  const getAllRecommendations = () => {
    const allRecommendations = state.items.flatMap(item => 
      item.product.recommendations || []
    );
    
    // Убираем дубликаты по id
    const uniqueRecommendations = allRecommendations.filter((rec, index, self) => 
      index === self.findIndex(r => r.id === rec.id)
    );
    
    return uniqueRecommendations;
  };

  const recommendations = getAllRecommendations();

  const handleAddRecommendation = (recommendationId: string) => {
    const product = products.find(p => p.id === recommendationId);
    if (product) {
      addItem(product, [], []);
    }
  };

  if (state.items.length === 0) {
    return (
      <div className="min-h-screen bg-mandarin-bg flex flex-col">
        <div className="bg-mandarin-card shadow-lg px-4 py-4 flex items-center border-b border-gray-600">
          <button onClick={onBack} className="mr-4">
            <ArrowLeft size={24} className="text-gray-300" />
          </button>
          <h1 className="text-xl font-semibold text-white">Корзина</h1>
        </div>

        <div className="flex-1 flex items-center justify-center px-6">
          <div className="text-center">
            <ShoppingBag size={80} className="text-gray-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Корзина пуста</h2>
            <p className="text-gray-400 mb-6">Добавьте товары из каталога</p>
            <button
              onClick={onBack}
              className="bg-gradient-to-r from-mandarin-orange to-yellow-500 text-white px-8 py-3 rounded-2xl font-semibold hover:from-yellow-500 hover:to-mandarin-orange transition-all duration-200"
            >
              Перейти к покупкам
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mandarin-bg flex flex-col pb-20">
      <div className="bg-mandarin-card shadow-lg px-4 py-4 flex items-center justify-between border-b border-gray-600">
        <div className="flex items-center">
          <button onClick={onBack} className="mr-4">
            <ArrowLeft size={24} className="text-gray-300" />
          </button>
          <h1 className="text-xl font-semibold text-white">Корзина</h1>
        </div>
        <span className="bg-mandarin-orange text-white px-3 py-1 rounded-full text-sm font-medium">
          {state.items.length} товар(ов)
        </span>
      </div>

      <div className="flex-1 px-4 py-4 space-y-4 overflow-y-auto pb-32">
        {state.items.map((item) => (
          <div key={`${item.product.id}-${item.selectedAddons.map(a => a.id).join('-')}-${item.selectedRecommendations.map(r => r.id).join('-')}`} className="bg-mandarin-card rounded-2xl p-4 shadow-lg border border-gray-600">
            <div className="flex items-center space-x-4">
              <img
                src={item.product.image}
                alt={item.product.name}
                className="w-16 h-16 rounded-xl object-cover"
              />
              <div className="flex-1">
                <h3 className="font-semibold text-white">{item.product.name}</h3>
                <p className="text-gray-400 text-sm">{item.product.description}</p>
                
                {/* Допы */}
                {item.selectedAddons.length > 0 && (
                  <div className="mt-1">
                    <span className="text-xs text-gray-500">Добавки: </span>
                    <span className="text-xs text-mandarin-orange">
                      {item.selectedAddons.map(addon => addon.name).join(', ')}
                    </span>
                  </div>
                )}
                
                {/* Рекомендации */}
                {item.selectedRecommendations.length > 0 && (
                  <div className="mt-1">
                    <span className="text-xs text-gray-500">Дополнительно: </span>
                    <span className="text-xs text-green-400">
                      {item.selectedRecommendations.map(rec => rec.name).join(', ')}
                    </span>
                  </div>
                )}
                
                <span className="text-lg font-bold text-mandarin-orange">
                  ₽{(item.product.price + 
                    item.selectedAddons.reduce((sum, addon) => sum + addon.price, 0) +
                    item.selectedRecommendations.reduce((sum, rec) => sum + rec.price, 0)
                  )}
                </span>
              </div>
              <button
                onClick={() => removeItem(item.product.id)}
                className="text-red-400 p-2 hover:bg-red-900/20 rounded-full transition-colors"
              >
                <Trash2 size={18} />
              </button>
            </div>
            
            <div className="flex items-center justify-between mt-4">
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => updateQuantity(item.product.id, item.quantity - 1)}
                  className="bg-gray-700 p-2 rounded-full hover:bg-gray-600 transition-colors"
                >
                  <Minus size={18} className="text-gray-300" />
                </button>
                <span className="text-lg font-semibold w-8 text-center text-white">{item.quantity}</span>
                <button
                  onClick={() => updateQuantity(item.product.id, item.quantity + 1)}
                  className="bg-mandarin-orange p-2 rounded-full hover:bg-yellow-500 transition-colors"
                >
                  <Plus size={18} className="text-white" />
                </button>
              </div>
              <span className="text-lg font-bold text-white">
                ₽{((item.product.price + 
                  item.selectedAddons.reduce((sum, addon) => sum + addon.price, 0) +
                  item.selectedRecommendations.reduce((sum, rec) => sum + rec.price, 0)
                ) * item.quantity).toLocaleString()}
              </span>
            </div>
          </div>
        ))}

        {/* Блок рекомендаций */}
        {recommendations.length > 0 && (
          <div className="bg-mandarin-card rounded-2xl p-4 shadow-lg border border-gray-600">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Отлично дополнит ваш заказ</h3>
              <button
                onClick={() => setShowRecommendations(!showRecommendations)}
                className="text-mandarin-orange hover:text-yellow-500 transition-colors"
              >
                {showRecommendations ? <X size={20} /> : <Plus size={20} />}
              </button>
            </div>
            
            {showRecommendations && (
              <div className="space-y-3">
                {recommendations.map((recommendation) => (
                  <div
                    key={recommendation.id}
                    className="flex items-center justify-between p-3 bg-gray-700 rounded-xl hover:bg-gray-600 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <img
                        src={recommendation.image}
                        alt={recommendation.name}
                        className="w-12 h-12 rounded-lg object-cover"
                      />
                      <div>
                        <div className="font-medium text-white">{recommendation.name}</div>
                        <div className="text-sm text-mandarin-orange">₽{recommendation.price}</div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleAddRecommendation(recommendation.id)}
                      className="bg-mandarin-orange text-white p-2 rounded-full hover:bg-yellow-500 transition-colors"
                    >
                      <Plus size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="fixed bottom-20 left-0 right-0 bg-mandarin-card p-4 border-t border-gray-600 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <span className="text-lg font-semibold text-white">Итого:</span>
          <span className="text-2xl font-bold text-mandarin-orange">₽{state.total.toLocaleString()}</span>
        </div>
        <button
          onClick={onCheckout}
          className="w-full bg-gradient-to-r from-mandarin-orange to-yellow-500 text-white py-4 rounded-2xl font-semibold text-lg hover:from-yellow-500 hover:to-mandarin-orange transition-all duration-200 transform hover:scale-[1.02]"
        >
          Оформить заказ
        </button>
      </div>
    </div>
  );
};