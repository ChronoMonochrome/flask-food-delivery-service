import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { CartItem, Product, Addon, Recommendation, WokCustomization } from '../types';

interface CartState {
  items: CartItem[];
  total: number;
}

type CartAction = 
  | { type: 'ADD_ITEM'; payload: { product: Product; addons: Addon[]; recommendations: Recommendation[]; customWok?: WokCustomization } }
  | { type: 'REMOVE_ITEM'; payload: { itemKey: string } }
  | { type: 'UPDATE_QUANTITY'; payload: { itemKey: string; quantity: number } }
  | { type: 'CLEAR_CART' };

// Функция для создания уникального ключа товара
export const createItemKey = (product: Product, addons: Addon[], recommendations: Recommendation[], customWok?: WokCustomization) => {
  const addonIds = addons.map(a => a.id).sort().join('-');
  const recIds = recommendations.map(r => r.id).sort().join('-');
  const wokKey = customWok ? 
    `${customWok.base.id}-${customWok.meats.map(m => m.id).sort().join(',')}-${customWok.toppings.map(t => t.id).sort().join(',')}-${customWok.sauces.map(s => s.id).sort().join(',')}` 
    : '';
  return `${product.id}-${addonIds}-${recIds}-${wokKey}`;
};

const cartReducer = (state: CartState, action: CartAction): CartState => {
  switch (action.type) {
    case 'ADD_ITEM': {
      const { product, addons, recommendations, customWok } = action.payload;
      
      const newItemKey = createItemKey(product, addons, recommendations, customWok);
      
      // Ищем существующий товар с точно такой же комбинацией
      const existingItemIndex = state.items.findIndex(item => {
        const existingKey = createItemKey(item.product, item.selectedAddons, item.selectedRecommendations, item.customWok);
        return existingKey === newItemKey;
      });
      
      if (existingItemIndex !== -1) {
        // Если найден точно такой же товар с такими же добавками - увеличиваем количество
        const updatedItems = [...state.items];
        updatedItems[existingItemIndex] = {
          ...updatedItems[existingItemIndex],
          quantity: updatedItems[existingItemIndex].quantity + 1
        };
        return {
          items: updatedItems,
          total: calculateTotal(updatedItems)
        };
      } else {
        // Если не найден - добавляем как новую позицию
        const newItems = [...state.items, { 
          product, 
          quantity: 1, 
          selectedAddons: addons,
          selectedRecommendations: recommendations,
          customWok
        }];
        return {
          items: newItems,
          total: calculateTotal(newItems)
        };
      }
    }
    
    case 'REMOVE_ITEM': {
      const newItems = state.items.filter(item => {
        const itemKey = createItemKey(item.product, item.selectedAddons, item.selectedRecommendations, item.customWok);
        return itemKey !== action.payload.itemKey;
      });
      return {
        items: newItems,
        total: calculateTotal(newItems)
      };
    }
    
    case 'UPDATE_QUANTITY': {
      if (action.payload.quantity <= 0) {
        const newItems = state.items.filter(item => {
          const itemKey = createItemKey(item.product, item.selectedAddons, item.selectedRecommendations, item.customWok);
          return itemKey !== action.payload.itemKey;
        });
        return {
          items: newItems,
          total: calculateTotal(newItems)
        };
      }
      
      const updatedItems = state.items.map(item => {
        const itemKey = createItemKey(item.product, item.selectedAddons, item.selectedRecommendations, item.customWok);
        return itemKey === action.payload.itemKey
          ? { ...item, quantity: action.payload.quantity }
          : item;
      });
      return {
        items: updatedItems,
        total: calculateTotal(updatedItems)
      };
    }
    
    case 'CLEAR_CART':
      return { items: [], total: 0 };
      
    default:
      return state;
  }
};

const calculateTotal = (items: CartItem[]): number => {
  return items.reduce((sum, item) => {
    let itemPrice = item.product.price + 
      item.selectedAddons.reduce((addonSum, addon) => addonSum + addon.price, 0) +
      item.selectedRecommendations.reduce((recSum, rec) => recSum + rec.price, 0);
    
    // Для кастомного WOK цена уже включена в product.price
    if (item.customWok) {
      // Цена уже рассчитана в WokBuilder и включена в product.price
      itemPrice = item.product.price;
    }
    
    return sum + (itemPrice * item.quantity);
  }, 0);
};

interface CartContextValue {
  state: CartState;
  addItem: (product: Product, addons: Addon[], recommendations: Recommendation[], customWok?: WokCustomization) => void;
  removeItem: (itemKey: string) => void;
  updateQuantity: (itemKey: string, quantity: number) => void;
  clearCart: () => void;
}

const CartContext = createContext<CartContextValue | null>(null);

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};

interface CartProviderProps {
  children: ReactNode;
}

export const CartProvider: React.FC<CartProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(cartReducer, { items: [], total: 0 });

  const addItem = (product: Product, addons: Addon[], recommendations: Recommendation[], customWok?: WokCustomization) => {
    dispatch({ type: 'ADD_ITEM', payload: { product, addons, recommendations, customWok } });
  };

  const removeItem = (itemKey: string) => {
    dispatch({ type: 'REMOVE_ITEM', payload: { itemKey } });
  };

  const updateQuantity = (itemKey: string, quantity: number) => {
    dispatch({ type: 'UPDATE_QUANTITY', payload: { itemKey, quantity } });
  };

  const clearCart = () => {
    dispatch({ type: 'CLEAR_CART' });
  };

  return (
    <CartContext.Provider value={{ state, addItem, removeItem, updateQuantity, clearCart }}>
      {children}
    </CartContext.Provider>
  );
};