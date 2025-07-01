import React from 'react';
import { CheckCircle, Home } from 'lucide-react';

interface OrderSuccessProps {
  onBackToHome: () => void;
}

export const OrderSuccess: React.FC<OrderSuccessProps> = ({ onBackToHome }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-mandarin-orange to-yellow-500 flex items-center justify-center px-6">
      <div className="bg-mandarin-card rounded-3xl p-8 text-center shadow-2xl max-w-sm w-full border border-gray-600">
        <div className="mb-6">
          <CheckCircle size={80} className="text-green-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Заказ принят!</h1>
          <p className="text-gray-300">
            Мы получили ваш заказ и уже готовим его. Ожидайте звонка курьера.
          </p>
        </div>
        
        <div className="bg-gray-700 rounded-2xl p-4 mb-6 border border-gray-600">
          <h3 className="font-semibold text-white mb-2">Время доставки</h3>
          <p className="text-mandarin-orange font-bold text-lg">45-60 минут</p>
        </div>

        <button
          onClick={onBackToHome}
          className="w-full bg-gradient-to-r from-mandarin-orange to-yellow-500 text-white py-4 rounded-2xl font-semibold text-lg hover:from-yellow-500 hover:to-mandarin-orange transition-all duration-200 transform hover:scale-[1.02] flex items-center justify-center space-x-2"
        >
          <Home size={20} />
          <span>На главную</span>
        </button>
      </div>
    </div>
  );
};