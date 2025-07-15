import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { ArrowLeft, Locate as LocationOn, Phone, CreditCard, MessageSquare } from 'lucide-react';
import { useBackendCartSelector } from '../../entities/cart';
import { useClearCartMutation, useGetCartQuery } from '../../shared/api/cart-api';
import { navigationActions } from '../../features/navigation';
import { DeliveryInfo } from '../../shared/types';

export const CheckoutPage: React.FC = () => {
  const dispatch = useDispatch();
  const { totalItems, total } = useBackendCartSelector();
  const [clearCart] = useClearCartMutation();
  const { data: cartData } = useGetCartQuery();
  const [deliveryInfo, setDeliveryInfo] = useState<DeliveryInfo>({
    address: '',
    phone: '',
    paymentMethod: 'cash',
    comment: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleBack = () => {
    dispatch(navigationActions.navigateToPage('cart'));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulate order processing
    await new Promise(resolve => setTimeout(resolve, 2000));

    await clearCart();
    dispatch(navigationActions.navigateToPage('success'));
    setIsSubmitting(false);
  };

  const isFormValid = deliveryInfo.address.length > 0 && deliveryInfo.phone.length > 0;

  return (
    <div className="min-h-screen bg-mandarin-bg">
      {/* Header */}
      <div className="bg-mandarin-card border-b border-gray-600">
        <div className="flex items-center p-4">
          <button onClick={handleBack} className="mr-4 p-2 text-gray-400 hover:text-white">
            <ArrowLeft size={24} />
          </button>
          <h1 className="text-xl font-bold text-white">Оформление заказа</h1>
        </div>
      </div>

      <div className="max-w-2xl mx-auto p-4 space-y-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Address */}
          <div className="bg-mandarin-card border border-gray-600 rounded-2xl p-4">
            <div className="flex items-center mb-4">
              <LocationOn className="text-mandarin-orange mr-2" size={20} />
              <h2 className="text-lg font-bold text-white">Адрес доставки</h2>
            </div>
            <input
              type="text"
              value={deliveryInfo.address}
              onChange={(e) => setDeliveryInfo({ ...deliveryInfo, address: e.target.value })}
              placeholder="Введите адрес доставки"
              required
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:border-mandarin-orange focus:outline-none"
            />
          </div>

          {/* Phone */}
          <div className="bg-mandarin-card border border-gray-600 rounded-2xl p-4">
            <div className="flex items-center mb-4">
              <Phone className="text-mandarin-orange mr-2" size={20} />
              <h2 className="text-lg font-bold text-white">Номер телефона</h2>
            </div>
            <input
              type="tel"
              value={deliveryInfo.phone}
              onChange={(e) => setDeliveryInfo({ ...deliveryInfo, phone: e.target.value })}
              placeholder="+7 (999) 999-99-99"
              required
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:border-mandarin-orange focus:outline-none"
            />
          </div>

          {/* Payment Method */}
          <div className="bg-mandarin-card border border-gray-600 rounded-2xl p-4">
            <div className="flex items-center mb-4">
              <CreditCard className="text-mandarin-orange mr-2" size={20} />
              <h2 className="text-lg font-bold text-white">Способ оплаты</h2>
            </div>
            <div className="space-y-2">
              {[
                { value: 'cash', label: 'Наличными курьеру' },
                { value: 'card', label: 'Картой курьеру' },
                { value: 'online', label: 'Онлайн оплата' }
              ].map((option) => (
                <label key={option.value} className="flex items-center p-2 cursor-pointer">
                  <input
                    type="radio"
                    name="paymentMethod"
                    value={option.value}
                    checked={deliveryInfo.paymentMethod === option.value}
                    onChange={(e) => setDeliveryInfo({ ...deliveryInfo, paymentMethod: e.target.value as any })}
                    className="mr-3 text-mandarin-orange"
                  />
                  <span className="text-gray-300">{option.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Comment */}
          <div className="bg-mandarin-card border border-gray-600 rounded-2xl p-4">
            <div className="flex items-center mb-4">
              <MessageSquare className="text-mandarin-orange mr-2" size={20} />
              <h2 className="text-lg font-bold text-white">Комментарий к заказу</h2>
            </div>
            <textarea
              value={deliveryInfo.comment}
              onChange={(e) => setDeliveryInfo({ ...deliveryInfo, comment: e.target.value })}
              placeholder="Дополнительные пожелания..."
              rows={3}
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:border-mandarin-orange focus:outline-none resize-none"
            />
          </div>

          {/* Order Summary */}
          <div className="bg-mandarin-card border border-gray-600 rounded-2xl p-4">
            <h2 className="text-lg font-bold text-white mb-4">Ваш заказ</h2>
            <div className="space-y-2">
              {cartData?.items.map((item, index) => (
                <div key={index}>
                  <div className="flex justify-between">
                    <span className="text-gray-400">
                      Товар {item.productId} × {item.quantity}
                    </span>
                    <span className="font-medium text-white">
                      ₽{/* TODO: Рассчитать цену товара */}
                    </span>
                  </div>
                  {item.selectedAddons && item.selectedAddons.length > 0 && (
                    <div className="text-sm text-mandarin-orange ml-2">
                      + {item.selectedAddons.length} добавок
                    </div>
                  )}
                  {item.selectedRecommendations && item.selectedRecommendations.length > 0 && (
                    <div className="text-sm text-green-400 ml-2">
                      + {item.selectedRecommendations.length} дополнительно
                    </div>
                  )}
                </div>
              )) || (
                <div className="text-gray-400">Корзина пуста</div>
              )}
              <div className="border-t border-gray-600 pt-2 mt-4">
                <div className="flex justify-between">
                  <span className="text-lg font-bold text-white">Итого:</span>
                  <span className="text-lg font-bold text-mandarin-orange">₽{total.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={!isFormValid || isSubmitting}
            className={`w-full py-4 rounded-2xl text-lg font-bold transition-all ${
              isFormValid && !isSubmitting
                ? 'bg-gradient-to-r from-mandarin-orange to-yellow-500 text-white hover:from-yellow-500 hover:to-mandarin-orange transform hover:scale-105'
                : 'bg-gray-600 text-gray-400 cursor-not-allowed'
            }`}
          >
            {isSubmitting ? 'Обрабатываем заказ...' : `Заказать на ₽${total.toLocaleString()}`}
          </button>
        </form>
      </div>
    </div>
  );
};