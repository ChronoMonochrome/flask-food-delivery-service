import React, { useState } from 'react';
import { ArrowLeft, MapPin, Phone, CreditCard, MessageSquare } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { DeliveryInfo } from '../types';

interface CheckoutProps {
  onBack: () => void;
  onOrderComplete: () => void;
}

export const Checkout: React.FC<CheckoutProps> = ({ onBack, onOrderComplete }) => {
  const { state, clearCart } = useCart();
  const [deliveryInfo, setDeliveryInfo] = useState<DeliveryInfo>({
    address: '',
    phone: '',
    paymentMethod: 'cash',
    comment: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulate order processing
    await new Promise(resolve => setTimeout(resolve, 2000));

    //clearCart();
    onOrderComplete();
    setIsSubmitting(false);
  };

  const isFormValid = deliveryInfo.address.length > 0 && deliveryInfo.phone.length > 0;

  return (
    <div className="min-h-screen bg-mandarin-bg">
      <div className="bg-mandarin-card shadow-lg px-4 py-4 flex items-center border-b border-gray-600">
        <button onClick={onBack} className="mr-4">
          <ArrowLeft size={24} className="text-gray-300" />
        </button>
        <h1 className="text-xl font-semibold text-white">Оформление заказа</h1>
      </div>

      <form onSubmit={handleSubmit} className="px-4 py-6 space-y-6">
        {/* Address */}
        <div className="bg-mandarin-card rounded-2xl p-4 shadow-lg border border-gray-600">
          <div className="flex items-center mb-3">
            <MapPin size={20} className="text-mandarin-orange mr-2" />
            <h3 className="font-semibold text-white">Адрес доставки</h3>
          </div>
          <input
            type="text"
            value={deliveryInfo.address}
            onChange={(e) => setDeliveryInfo({ ...deliveryInfo, address: e.target.value })}
            placeholder="Введите адрес доставки"
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-xl focus:ring-2 focus:ring-mandarin-orange focus:border-mandarin-orange outline-none transition-colors text-white placeholder-gray-400"
            required
          />
        </div>

        {/* Phone */}
        <div className="bg-mandarin-card rounded-2xl p-4 shadow-lg border border-gray-600">
          <div className="flex items-center mb-3">
            <Phone size={20} className="text-mandarin-orange mr-2" />
            <h3 className="font-semibold text-white">Номер телефона</h3>
          </div>
          <input
            type="tel"
            value={deliveryInfo.phone}
            onChange={(e) => setDeliveryInfo({ ...deliveryInfo, phone: e.target.value })}
            placeholder="+7 (999) 999-99-99"
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-xl focus:ring-2 focus:ring-mandarin-orange focus:border-mandarin-orange outline-none transition-colors text-white placeholder-gray-400"
            required
          />
        </div>

        {/* Payment Method */}
        <div className="bg-mandarin-card rounded-2xl p-4 shadow-lg border border-gray-600">
          <div className="flex items-center mb-3">
            <CreditCard size={20} className="text-mandarin-orange mr-2" />
            <h3 className="font-semibold text-white">Способ оплаты</h3>
          </div>
          <div className="space-y-3">
            {[
              { value: 'cash', label: 'Наличными курьеру' },
              { value: 'card', label: 'Картой курьеру' },
              { value: 'online', label: 'Онлайн оплата' }
            ].map((method) => (
              <label key={method.value} className="flex items-center">
                <input
                  type="radio"
                  name="paymentMethod"
                  value={method.value}
                  checked={deliveryInfo.paymentMethod === method.value}
                  onChange={(e) => setDeliveryInfo({ ...deliveryInfo, paymentMethod: e.target.value as any })}
                  className="mr-3 text-mandarin-orange focus:ring-mandarin-orange bg-gray-700 border-gray-600"
                />
                <span className="text-gray-300">{method.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Comment */}
        <div className="bg-mandarin-card rounded-2xl p-4 shadow-lg border border-gray-600">
          <div className="flex items-center mb-3">
            <MessageSquare size={20} className="text-mandarin-orange mr-2" />
            <h3 className="font-semibold text-white">Комментарий к заказу</h3>
          </div>
          <textarea
            value={deliveryInfo.comment}
            onChange={(e) => setDeliveryInfo({ ...deliveryInfo, comment: e.target.value })}
            placeholder="Дополнительные пожелания..."
            rows={3}
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-xl focus:ring-2 focus:ring-mandarin-orange focus:border-mandarin-orange outline-none transition-colors resize-none text-white placeholder-gray-400"
          />
        </div>

        {/* Order Summary */}
        <div className="bg-mandarin-card rounded-2xl p-4 shadow-lg border border-gray-600">
          <h3 className="font-semibold text-white mb-3">Ваш заказ</h3>
          <div className="space-y-2">
            {state.items.map((item, index) => (
              <div key={index} className="text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-300">
                    {item.product.name} × {item.quantity}
                  </span>
                  <span className="font-medium text-white">
                    ₽{((item.product.price + 
                      item.selectedAddons.reduce((sum, addon) => sum + addon.price, 0) +
                      item.selectedRecommendations.reduce((sum, rec) => sum + rec.price, 0)
                    ) * item.quantity).toLocaleString()}
                  </span>
                </div>
                {item.selectedAddons.length > 0 && (
                  <div className="text-xs text-mandarin-orange ml-2">
                    + {item.selectedAddons.map(addon => addon.name).join(', ')}
                  </div>
                )}
                {item.selectedRecommendations.length > 0 && (
                  <div className="text-xs text-green-400 ml-2">
                    + {item.selectedRecommendations.map(rec => rec.name).join(', ')}
                  </div>
                )}
              </div>
            ))}
            <div className="border-t border-gray-600 pt-2 mt-3">
              <div className="flex justify-between text-lg font-bold">
                <span className="text-white">Итого:</span>
                <span className="text-mandarin-orange">₽{state.total.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={!isFormValid || isSubmitting}
          className={`w-full py-4 rounded-2xl font-semibold text-lg transition-all duration-200 ${
            isFormValid && !isSubmitting
              ? 'bg-gradient-to-r from-mandarin-orange to-yellow-500 text-white hover:from-yellow-500 hover:to-mandarin-orange transform hover:scale-[1.02]'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
          }`}
        >
          {isSubmitting ? 'Обрабатываем заказ...' : `Заказать на ₽${state.total.toLocaleString()}`}
        </button>
      </form>
    </div>
  );
};
