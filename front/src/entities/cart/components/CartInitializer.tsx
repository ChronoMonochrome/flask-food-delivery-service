import React, { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { useGetCartQuery } from '../../../shared/api/cart-api';
import { backendCartActions } from '../model/backend-slice';

export const CartInitializer: React.FC = () => {
  const dispatch = useDispatch();
  
  // Загружаем корзину при старте приложения
  const { data: cartData, isLoading, error } = useGetCartQuery(undefined, {
    // Обновляем каждые 30 секунд для синхронизации
    pollingInterval: 30000,
    // Перезагружаем при фокусе на окно
    refetchOnFocus: true,
    // Перезагружаем при восстановлении соединения
    refetchOnReconnect: true,
    // Не показываем старые данные при обновлении
    refetchOnMountOrArgChange: false,
  });

  useEffect(() => {
    if (cartData) {
      // Преобразуем данные корзины в кэш количества товаров
      const productQuantities: Record<string, number> = {};
      let totalItems = 0;

      cartData.items.forEach((item) => {
        // Для простых товаров без кастомизации учитываем в кэше
        if (!item.customWok && item.selectedAddons.length === 0) {
          productQuantities[item.productId] = (productQuantities[item.productId] || 0) + item.quantity;
        }
        totalItems += item.quantity;
      });

      // Используем умное обновление вместо полной перезаписи
      dispatch(backendCartActions.updateProductQuantities({
        productQuantities,
        totalItems,
        total: cartData.total
      }));
    }
  }, [cartData, dispatch]);

  // Не устанавливаем глобальный loading для фонового обновления
  // useEffect(() => {
  //   dispatch(backendCartActions.setLoading(isLoading));
  // }, [isLoading, dispatch]);

  // Этот компонент не рендерит ничего видимого
  return null;
};