import React from 'react';
import { Home, ShoppingCart, ClipboardList } from 'lucide-react';
import { useCart } from '../context/CartContext';

interface BottomNavProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ currentPage, onNavigate }) => {
  const { state } = useCart();

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-mandarin-card border-t border-gray-600 px-4 py-2 safe-area-pb">
      <div className="flex items-center justify-around">
        <button
          onClick={() => onNavigate('home')}
          className={`flex flex-col items-center p-2 rounded-xl transition-colors ${
            currentPage === 'home'
              ? 'text-mandarin-orange bg-mandarin-orange/20'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <Home size={24} />
          <span className="text-xs mt-1">Главная</span>
        </button>

        <button
          onClick={() => onNavigate('cart')}
          className={`relative flex flex-col items-center p-2 rounded-xl transition-colors ${
            currentPage === 'cart'
              ? 'text-mandarin-orange bg-mandarin-orange/20'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <ShoppingCart size={24} />
          {state.items.length > 0 && (
            <span className="absolute -top-1 -right-1 bg-mandarin-orange text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {state.items.length}
            </span>
          )}
          <span className="text-xs mt-1">Корзина</span>
        </button>

        <button
          onClick={() => onNavigate('orders')}
          className={`flex flex-col items-center p-2 rounded-xl transition-colors ${
            currentPage === 'orders'
              ? 'text-mandarin-orange bg-mandarin-orange/20'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <ClipboardList size={24} />
          <span className="text-xs mt-1">Заказы</span>
        </button>
      </div>
    </div>
  );
};