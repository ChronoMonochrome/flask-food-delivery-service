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
    // Обновляем кэш количества товаров из ответа бэкенда
    updateProductQuantities: (state, action: PayloadAction<{ productQuantities: Record<string, number>; totalItems: number; total: number }>) => {
      state.productQuantities = action.payload.productQuantities;
      state.totalItems = action.payload.totalItems;
      state.total = action.payload.total;
    },
    
    // Оптимистичное обновление для быстрого отклика UI
    optimisticUpdateQuantity: (state, action: PayloadAction<{ productId: string; quantity: number }>) => {
      const { productId, quantity } = action.payload;
      const oldQuantity = state.productQuantities[productId] || 0;
      
      if (quantity <= 0) {
        delete state.productQuantities[productId];
      } else {
        state.productQuantities[productId] = quantity;
      }
      
      // Обновляем общее количество
      state.totalItems = state.totalItems - oldQuantity + Math.max(0, quantity);
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