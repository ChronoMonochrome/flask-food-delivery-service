import React from 'react';
import { Plus } from 'lucide-react';
import { Product } from '../types';
import { useCart } from '../context/CartContext';

interface ProductCardProps {
  product: Product;
  onProductClick: (product: Product) => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, onProductClick }) => {
  const { addItem } = useCart();

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    addItem(product, [], []);
  };

  return (
    <div
      onClick={() => onProductClick(product)}
      className="bg-mandarin-card rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer transform hover:scale-[1.02] border border-gray-600"
    >
      <div className="relative">
        <img
          src={product.image}
          alt={product.name}
          className="w-full h-48 object-cover rounded-t-2xl"
        />
        <button
          onClick={handleAddToCart}
          className="absolute bottom-3 right-3 bg-gradient-to-r from-mandarin-orange to-yellow-500 text-white p-2 rounded-full shadow-lg hover:from-yellow-500 hover:to-mandarin-orange transition-all duration-200 transform hover:scale-110"
        >
          <Plus size={20} />
        </button>
      </div>
      
      <div className="p-4">
        <h3 className="font-bold text-lg text-white mb-2">{product.name}</h3>
        <p className="text-gray-300 text-sm mb-3 line-clamp-2">{product.description}</p>
        
        {/* КБЖУ */}
        <div className="bg-gray-700 rounded-lg p-2 mb-3">
          <div className="text-xs text-gray-400 mb-1">КБЖУ на 100г:</div>
          <div className="grid grid-cols-4 gap-1 text-xs">
            <div className="text-center">
              <div className="text-mandarin-orange font-semibold">{product.nutrition.calories}</div>
              <div className="text-gray-500">ккал</div>
            </div>
            <div className="text-center">
              <div className="text-blue-400 font-semibold">{product.nutrition.protein}</div>
              <div className="text-gray-500">белки</div>
            </div>
            <div className="text-center">
              <div className="text-yellow-400 font-semibold">{product.nutrition.fat}</div>
              <div className="text-gray-500">жиры</div>
            </div>
            <div className="text-center">
              <div className="text-green-400 font-semibold">{product.nutrition.carbs}</div>
              <div className="text-gray-500">углев</div>
            </div>
          </div>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-2xl font-bold text-white">₽{product.price}</span>
        </div>
      </div>
    </div>
  );
};