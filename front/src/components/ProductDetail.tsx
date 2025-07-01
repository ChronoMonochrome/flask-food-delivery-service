import React, { useState } from 'react';
import { ArrowLeft, Plus, Minus, Check } from 'lucide-react';
import { Product, Addon, Recommendation } from '../types';
import { useCart } from '../context/CartContext';

interface ProductDetailProps {
  product: Product;
  onBack: () => void;
}

export const ProductDetail: React.FC<ProductDetailProps> = ({ product, onBack }) => {
  const { state, addItem, updateQuantity } = useCart();
  const [selectedAddons, setSelectedAddons] = useState<Addon[]>([]);
  const [selectedRecommendations, setSelectedRecommendations] = useState<Recommendation[]>([]);
  
  const cartItem = state.items.find(item => item.product.id === product.id);
  const quantity = cartItem?.quantity || 0;

  const handleAddonToggle = (addon: Addon) => {
    setSelectedAddons(prev => 
      prev.find(a => a.id === addon.id)
        ? prev.filter(a => a.id !== addon.id)
        : [...prev, addon]
    );
  };

  const handleRecommendationToggle = (recommendation: Recommendation) => {
    setSelectedRecommendations(prev => 
      prev.find(r => r.id === recommendation.id)
        ? prev.filter(r => r.id !== recommendation.id)
        : [...prev, recommendation]
    );
  };

  const handleAddToCart = () => {
    addItem(product, selectedAddons, selectedRecommendations);
  };

  const handleQuantityChange = (newQuantity: number) => {
    if (newQuantity <= 0) {
      updateQuantity(product.id, 0);
    } else {
      updateQuantity(product.id, newQuantity);
    }
  };

  const totalPrice = product.price + 
    selectedAddons.reduce((sum, addon) => sum + addon.price, 0) +
    selectedRecommendations.reduce((sum, rec) => sum + rec.price, 0);

  return (
    <div className="min-h-screen bg-mandarin-bg">
      <div className="relative">
        <img
          src={product.image}
          alt={product.name}
          className="w-full h-80 object-cover"
        />
        <button
          onClick={onBack}
          className="absolute top-4 left-4 bg-mandarin-card/90 backdrop-blur-sm p-2 rounded-full shadow-lg border border-gray-600"
        >
          <ArrowLeft size={24} className="text-white" />
        </button>
      </div>

      <div className="bg-mandarin-card rounded-t-3xl -mt-6 relative z-10 px-6 py-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-white">{product.name}</h1>
          <span className="text-3xl font-bold text-mandarin-orange">₽{product.price}</span>
        </div>

        <p className="text-gray-300 text-lg leading-relaxed mb-6">
          {product.description}
        </p>

        {/* КБЖУ */}
        <div className="bg-gray-700 rounded-2xl p-4 mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">КБЖУ на 100г:</h3>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-mandarin-orange">{product.nutrition.calories}</div>
              <div className="text-gray-400 text-sm">ккал</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400">{product.nutrition.protein}</div>
              <div className="text-gray-400 text-sm">белки</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-400">{product.nutrition.fat}</div>
              <div className="text-gray-400 text-sm">жиры</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">{product.nutrition.carbs}</div>
              <div className="text-gray-400 text-sm">углеводы</div>
            </div>
          </div>
        </div>

        {product.ingredients && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-white mb-3">Состав:</h3>
            <div className="flex flex-wrap gap-2">
              {product.ingredients.map((ingredient, index) => (
                <span
                  key={index}
                  className="bg-gray-700 text-gray-300 px-3 py-1 rounded-full text-sm border border-gray-600"
                >
                  {ingredient}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Допы */}
        {product.availableAddons && product.availableAddons.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-white mb-3">Добавки:</h3>
            <div className="space-y-2">
              {product.availableAddons.map((addon) => (
                <button
                  key={addon.id}
                  onClick={() => handleAddonToggle(addon)}
                  className={`w-full flex items-center justify-between p-3 rounded-xl transition-colors ${
                    selectedAddons.find(a => a.id === addon.id)
                      ? 'bg-mandarin-orange text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  <span>{addon.name}</span>
                  <div className="flex items-center space-x-2">
                    <span>+₽{addon.price}</span>
                    {selectedAddons.find(a => a.id === addon.id) && (
                      <Check size={18} />
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Рекомендации */}
        {product.recommendations && product.recommendations.length > 0 && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-white mb-3">Отлично сочетается:</h3>
            <div className="space-y-3">
              {product.recommendations.map((recommendation) => (
                <button
                  key={recommendation.id}
                  onClick={() => handleRecommendationToggle(recommendation)}
                  className={`w-full flex items-center p-3 rounded-xl transition-colors ${
                    selectedRecommendations.find(r => r.id === recommendation.id)
                      ? 'bg-mandarin-orange text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  <img
                    src={recommendation.image}
                    alt={recommendation.name}
                    className="w-12 h-12 rounded-lg object-cover mr-3"
                  />
                  <div className="flex-1 text-left">
                    <div className="font-medium">{recommendation.name}</div>
                    <div className="text-sm opacity-75">+₽{recommendation.price}</div>
                  </div>
                  {selectedRecommendations.find(r => r.id === recommendation.id) && (
                    <Check size={18} />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="sticky bottom-0 bg-mandarin-card pt-4 border-t border-gray-600">
          {quantity > 0 ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => handleQuantityChange(quantity - 1)}
                  className="bg-gray-700 p-2 rounded-full hover:bg-gray-600 transition-colors"
                >
                  <Minus size={20} className="text-gray-300" />
                </button>
                <span className="text-xl font-semibold text-white">{quantity}</span>
                <button
                  onClick={() => handleQuantityChange(quantity + 1)}
                  className="bg-mandarin-orange p-2 rounded-full hover:bg-yellow-500 transition-colors"
                >
                  <Plus size={20} className="text-white" />
                </button>
              </div>
              <span className="text-xl font-bold text-white">
                ₽{(totalPrice * quantity).toLocaleString()}
              </span>
            </div>
          ) : (
            <button
              onClick={handleAddToCart}
              className="w-full bg-gradient-to-r from-mandarin-orange to-yellow-500 text-white py-4 rounded-2xl font-semibold text-lg hover:from-yellow-500 hover:to-mandarin-orange transition-all duration-200 transform hover:scale-[1.02]"
            >
              Добавить в корзину - ₽{totalPrice.toLocaleString()}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};