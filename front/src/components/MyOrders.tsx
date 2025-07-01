import React from 'react';
import { ArrowLeft, Clock, CheckCircle, Truck, XCircle, Package, ClipboardList } from 'lucide-react';
import { mockOrders } from '../data/mockData';

interface MyOrdersProps {
  onBack: () => void;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'pending':
      return <Clock size={20} className="text-yellow-400" />;
    case 'preparing':
      return <Package size={20} className="text-blue-400" />;
    case 'delivering':
      return <Truck size={20} className="text-mandarin-orange" />;
    case 'delivered':
      return <CheckCircle size={20} className="text-green-400" />;
    case 'cancelled':
      return <XCircle size={20} className="text-red-400" />;
    default:
      return <Clock size={20} className="text-gray-400" />;
  }
};

const getStatusText = (status: string) => {
  switch (status) {
    case 'pending':
      return 'Ожидает подтверждения';
    case 'preparing':
      return 'Готовится';
    case 'delivering':
      return 'В пути';
    case 'delivered':
      return 'Доставлен';
    case 'cancelled':
      return 'Отменен';
    default:
      return 'Неизвестно';
  }
};

const formatDate = (date: Date) => {
  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

export const MyOrders: React.FC<MyOrdersProps> = ({ onBack }) => {
  return (
    <div className="min-h-screen bg-mandarin-bg">
      <div className="bg-mandarin-card shadow-lg px-4 py-4 flex items-center border-b border-gray-600">
        <button onClick={onBack} className="mr-4">
          <ArrowLeft size={24} className="text-gray-300" />
        </button>
        <h1 className="text-xl font-semibold text-white">Мои заказы</h1>
      </div>

      <div className="px-4 py-6 space-y-4">
        {mockOrders.map((order) => (
          <div key={order.id} className="bg-mandarin-card rounded-2xl p-4 shadow-lg border border-gray-600">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                {getStatusIcon(order.status)}
                <span className="font-semibold text-white">Заказ #{order.id}</span>
              </div>
              <span className="text-sm text-gray-400">
                {formatDate(order.createdAt)}
              </span>
            </div>

            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400">Статус:</span>
                <span className="font-medium text-white">{getStatusText(order.status)}</span>
              </div>
              
              {order.estimatedDelivery && order.status === 'delivering' && (
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-400">Ожидаемое время:</span>
                  <span className="font-medium text-mandarin-orange">
                    {formatDate(order.estimatedDelivery)}
                  </span>
                </div>
              )}
              
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Адрес:</span>
                <span className="font-medium text-white text-right flex-1 ml-2">
                  {order.deliveryInfo.address}
                </span>
              </div>
            </div>

            <div className="border-t border-gray-600 pt-4">
              <h4 className="font-semibold text-white mb-2">Состав заказа:</h4>
              <div className="space-y-2">
                {order.items.map((item, index) => (
                  <div key={index} className="flex justify-between text-sm">
                    <div className="flex-1">
                      <span className="text-gray-300">
                        {item.product.name} × {item.quantity}
                      </span>
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
                    <span className="font-medium text-white">
                      ₽{((item.product.price + 
                        item.selectedAddons.reduce((sum, addon) => sum + addon.price, 0) +
                        item.selectedRecommendations.reduce((sum, rec) => sum + rec.price, 0)
                      ) * item.quantity).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
              
              <div className="border-t border-gray-600 pt-2 mt-3">
                <div className="flex justify-between text-lg font-bold">
                  <span className="text-white">Итого:</span>
                  <span className="text-mandarin-orange">₽{order.total.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
        
        {mockOrders.length === 0 && (
          <div className="text-center py-12">
            <ClipboardList size={80} className="text-gray-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Заказов пока нет</h2>
            <p className="text-gray-400">Сделайте свой первый заказ!</p>
          </div>
        )}
      </div>
    </div>
  );
};