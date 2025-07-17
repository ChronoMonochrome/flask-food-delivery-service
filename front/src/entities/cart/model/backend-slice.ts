import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Product } from '../../../shared/types';

// Новый стейт для работы с бэкендом
export interface BackendCartState {
  // Кэш количества товаров для быстрого отображения в карточках
  productQuantities: Record<string, number>; // productId -> quantity
  // Общее количество товаров в корзине
  totalItems: number;
  // Общая стоимость
  total: number;
  // Флаг загрузки
  isLoading: boolean;
}

const initialState: BackendCartState = {
  productQuantities: {},
  totalItems: 0,
  total: 0,
  isLoading: false,
};

export const backendCartSlice = createSlice({
  name: 'backendCart',
  initialState,
  reducers: {
    // Умное обновление - мержим данные вместо полной перезаписи
    updateProductQuantities: (state, action: PayloadAction<{ productQuantities: Record<string, number>; totalItems: number; total: number }>) => {
      const { productQuantities, totalItems, total } = action.payload;
      
      // Обновляем только изменившиеся товары
      Object.keys(productQuantities).forEach(productId => {
        const newQuantity = productQuantities[productId];
        const currentQuantity = state.productQuantities[productId] || 0;
        
        // Обновляем только если количество действительно изменилось
        if (newQuantity !== currentQuantity) {
          if (newQuantity > 0) {
            state.productQuantities[productId] = newQuantity;
          } else {
            delete state.productQuantities[productId];
          }
        }
      });
      
      // Удаляем товары, которых больше нет в ответе бэкенда
      Object.keys(state.productQuantities).forEach(productId => {
        if (!(productId in productQuantities)) {
          delete state.productQuantities[productId];
        }
      });
      
      // Обновляем общие данные только при изменении
      if (state.totalItems !== totalItems) {
        state.totalItems = totalItems;
      }
      if (state.total !== total) {
        state.total = total;
      }
    },
    
    // Оптимистичное обновление с защитой от перезаписи
    optimisticUpdateQuantity: (state, action: PayloadAction<{ productId: string; quantity: number; isTemporary?: boolean }>) => {
      const { productId, quantity, isTemporary = false } = action.payload;
      const oldQuantity = state.productQuantities[productId] || 0;
      
      if (quantity <= 0) {
        delete state.productQuantities[productId];
      } else {
        state.productQuantities[productId] = quantity;
      }
      
      // Обновляем общее количество
      state.totalItems = state.totalItems - oldQuantity + Math.max(0, quantity);
    },
    
    // Новый экшен для временного сброса при загрузке
    setTemporaryLoading: (state, action: PayloadAction<boolean>) => {
      // Не сбрасываем данные, только устанавливаем флаг
      state.isLoading = action.payload;
    },
    
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    
    clearCache: (state) => {
      state.productQuantities = {};
      state.totalItems = 0;
      state.total = 0;
    },
  },
});

export const backendCartActions = backendCartSlice.actions;