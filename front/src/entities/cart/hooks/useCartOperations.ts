import { useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { 
  useAddToCartMutation, 
  useUpdateCartItemMutation, 
  useRemoveFromCartMutation,
  AddToCartRequest 
} from '../../../shared/api/cart-api';
import { backendCartActions } from '../model/backend-slice';
import { Product, Addon, Recommendation, WokCustomization } from '../../../shared/types';

export const useCartOperations = () => {
  const dispatch = useDispatch();
  const [addToCartMutation] = useAddToCartMutation();
  const [updateCartItemMutation] = useUpdateCartItemMutation();
  const [removeFromCartMutation] = useRemoveFromCartMutation();

  const addToCart = useCallback(async (
    product: Product,
    addons: Addon[] = [],
    recommendations: Recommendation[] = [],
    customWok?: WokCustomization
  ) => {
    // Оптимистичное обновление
    dispatch(backendCartActions.optimisticUpdateQuantity({
      productId: product.id,
      quantity: 1 // Предполагаем добавление 1 товара
    }));

    try {
      const request: AddToCartRequest = {
        productId: product.id,
        quantity: 1,
        addons: addons.map(addon => ({
          id: addon.id,
          quantity: addon.quantity || 1
        })),
        recommendations: recommendations.map(rec => rec.id),
        customWok: customWok ? {
          baseId: customWok.base.id,
          meatIds: customWok.meats.map(m => m.id),
          toppingIds: customWok.toppings.map(t => t.id),
          sauceIds: customWok.sauces.map(s => s.id),
        } : undefined,
        // Для кастомных товаров передаем дополнительную информацию
        customName: customWok ? product.name : undefined,
        customDescription: customWok ? product.description : undefined,
        customPrice: customWok ? product.price : undefined,
      };

      const result = await addToCartMutation(request).unwrap();
      
      // Обновляем кэш из ответа бэкенда
      updateCacheFromBackendResponse(result);
    } catch (error) {
      // Откатываем оптимистичное обновление при ошибке
      dispatch(backendCartActions.optimisticUpdateQuantity({
        productId: product.id,
        quantity: 0
      }));
      console.error('Ошибка добавления в корзину:', error);
    }
  }, [addToCartMutation, dispatch]);

  const updateQuantity = useCallback(async (itemId: string, productId: string, newQuantity: number) => {
    // Оптимистичное обновление
    dispatch(backendCartActions.optimisticUpdateQuantity({
      productId,
      quantity: newQuantity
    }));

    try {
      const result = await updateCartItemMutation({
        itemId,
        quantity: newQuantity
      }).unwrap();
      
      updateCacheFromBackendResponse(result);
    } catch (error) {
      // При ошибке нужно будет перезагрузить корзину
      console.error('Ошибка обновления количества:', error);
    }
  }, [updateCartItemMutation, dispatch]);

  const removeFromCart = useCallback(async (itemId: string, productId: string) => {
    // Оптимистичное обновление
    dispatch(backendCartActions.optimisticUpdateQuantity({
      productId,
      quantity: 0
    }));

    try {
      const result = await removeFromCartMutation({ itemId }).unwrap();
      updateCacheFromBackendResponse(result);
    } catch (error) {
      console.error('Ошибка удаления из корзины:', error);
    }
  }, [removeFromCartMutation, dispatch]);

  const updateCacheFromBackendResponse = useCallback((backendCart: any) => {
    // Преобразуем ответ бэкенда в кэш количества товаров
    const productQuantities: Record<string, number> = {};
    let totalItems = 0;

    if (backendCart.items) {
      backendCart.items.forEach((item: any) => {
        // Учитываем в кэше только простые товары без добавок и кастомизации
        if (!item.customWok && (!item.selectedAddons || item.selectedAddons.length === 0)) {
          productQuantities[item.productId] = (productQuantities[item.productId] || 0) + item.quantity;
        }
        totalItems += item.quantity;
      });
    }

    dispatch(backendCartActions.updateProductQuantities({
      productQuantities,
      totalItems,
      total: backendCart.total || 0
    }));
  }, [dispatch]);

  return {
    addToCart,
    updateQuantity,
    removeFromCart,
  };
};