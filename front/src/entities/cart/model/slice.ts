import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { CartItem, Product, Addon, Recommendation, WokCustomization } from '../../../shared/types';

export interface CartState {
  items: CartItem[];
  total: number;
}

interface AddItemPayload {
  product: Product;
  addons: Addon[];
  recommendations: Recommendation[];
  customWok?: WokCustomization;
}

interface UpdateQuantityPayload {
  itemKey: string;
  quantity: number;
}

interface RemoveItemPayload {
  itemKey: string;
}

export const createItemKey = (
  product: Product, 
  addons: Addon[], 
  recommendations: Recommendation[], 
  customWok?: WokCustomization
) => {
  const addonIds = addons.map(a => a.id).sort().join('-');
  const recIds = recommendations.map(r => r.id).sort().join('-');
  const wokKey = customWok ? 
    `${customWok.base.id}-${customWok.meats.map(m => m.id).sort().join(',')}-${customWok.toppings.map(t => t.id).sort().join(',')}-${customWok.sauces.map(s => s.id).sort().join(',')}` 
    : '';
  return `${product.id}-${addonIds}-${recIds}-${wokKey}`;
};

const calculateTotal = (items: CartItem[]): number => {
  return items.reduce((sum, item) => {
    let itemPrice = item.product.price;
    
    // Добавляем стоимость добавок (всегда учитываем)
    itemPrice += item.selectedAddons.reduce((addonSum, addon) => addonSum + (addon.price * (addon.quantity || 1)), 0);
    
    // Добавляем стоимость рекомендаций (только если не кастомный WOK)
    if (!item.customWok) {
      itemPrice += item.selectedRecommendations.reduce((recSum, rec) => recSum + rec.price, 0);
    }
    
    return sum + (itemPrice * item.quantity);
  }, 0);
};

const initialState: CartState = {
  items: [],
  total: 0,
};

export const cartSlice = createSlice({
  name: 'cart',
  initialState,
  reducers: {
    addItem: (state, action: PayloadAction<AddItemPayload>) => {
      const { product, addons, recommendations, customWok } = action.payload;
      
      const newItemKey = createItemKey(product, addons, recommendations, customWok);
      
      const existingItemIndex = state.items.findIndex(item => {
        const existingKey = createItemKey(item.product, item.selectedAddons, item.selectedRecommendations, item.customWok);
        return existingKey === newItemKey;
      });
      
      if (existingItemIndex !== -1) {
        state.items[existingItemIndex].quantity += 1;
      } else {
        state.items.push({ 
          product, 
          quantity: 1, 
          selectedAddons: addons,
          selectedRecommendations: recommendations,
          customWok
        });
      }
      
      state.total = calculateTotal(state.items);
    },
    
    removeItem: (state, action: PayloadAction<RemoveItemPayload>) => {
      state.items = state.items.filter(item => {
        const itemKey = createItemKey(item.product, item.selectedAddons, item.selectedRecommendations, item.customWok);
        return itemKey !== action.payload.itemKey;
      });
      state.total = calculateTotal(state.items);
    },
    
    updateQuantity: (state, action: PayloadAction<UpdateQuantityPayload>) => {
      const { itemKey, quantity } = action.payload;
      
      if (quantity <= 0) {
        state.items = state.items.filter(item => {
          const currentItemKey = createItemKey(item.product, item.selectedAddons, item.selectedRecommendations, item.customWok);
          return currentItemKey !== itemKey;
        });
      } else {
        const itemIndex = state.items.findIndex(item => {
          const currentItemKey = createItemKey(item.product, item.selectedAddons, item.selectedRecommendations, item.customWok);
          return currentItemKey === itemKey;
        });
        
        if (itemIndex !== -1) {
          state.items[itemIndex].quantity = quantity;
        }
      }
      
      state.total = calculateTotal(state.items);
    },
    
    clearCart: (state) => {
      state.items = [];
      state.total = 0;
    },
  },
});

export const cartActions = cartSlice.actions;