import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { CartItem, Product, Addon, Recommendation } from '../types';

interface CartState {
  items: CartItem[];
  total: number;
}

type CartAction = 
  | { type: 'ADD_ITEM'; payload: { product: Product; addons: Addon[]; recommendations: Recommendation[] } }
  | { type: 'REMOVE_ITEM'; payload: string }
  | { type: 'UPDATE_QUANTITY'; payload: { id: string; quantity: number } }
  | { type: 'CLEAR_CART' };

const cartReducer = (state: CartState, action: CartAction): CartState => {
  switch (action.type) {
    case 'ADD_ITEM': {
      const { product, addons, recommendations } = action.payload;
      const itemKey = `${product.id}-${addons.map(a => a.id).join('-')}-${recommendations.map(r => r.id).join('-')}`;
      
      const existingItem = state.items.find(item => 
        item.product.id === product.id &&
        JSON.stringify(item.selectedAddons) === JSON.stringify(addons) &&
        JSON.stringify(item.selectedRecommendations) === JSON.stringify(recommendations)
      );
      
      if (existingItem) {
        const updatedItems = state.items.map(item =>
          item === existingItem
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
        return {
          items: updatedItems,
          total: calculateTotal(updatedItems)
        };
      }
      
      const newItems = [...state.items, { 
        product, 
        quantity: 1, 
        selectedAddons: addons,
        selectedRecommendations: recommendations
      }];
      return {
        items: newItems,
        total: calculateTotal(newItems)
      };
    }
    
    case 'REMOVE_ITEM': {
      const newItems = state.items.filter(item => item.product.id !== action.payload);
      return {
        items: newItems,
        total: calculateTotal(newItems)
      };
    }
    
    case 'UPDATE_QUANTITY': {
      if (action.payload.quantity <= 0) {
        const newItems = state.items.filter(item => item.product.id !== action.payload.id);
        return {
          items: newItems,
          total: calculateTotal(newItems)
        };
      }
      
      const updatedItems = state.items.map(item =>
        item.product.id === action.payload.id
          ? { ...item, quantity: action.payload.quantity }
          : item
      );
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
    const itemPrice = item.product.price + 
      item.selectedAddons.reduce((addonSum, addon) => addonSum + addon.price, 0) +
      item.selectedRecommendations.reduce((recSum, rec) => recSum + rec.price, 0);
    return sum + (itemPrice * item.quantity);
  }, 0);
};

interface CartContextValue {
  state: CartState;
  addItem: (product: Product, addons: Addon[], recommendations: Recommendation[]) => void;
  removeItem: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
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

  const addItem = (product: Product, addons: Addon[], recommendations: Recommendation[]) => {
    dispatch({ type: 'ADD_ITEM', payload: { product, addons, recommendations } });
  };

  const removeItem = (productId: string) => {
    dispatch({ type: 'REMOVE_ITEM', payload: productId });
  };

  const updateQuantity = (productId: string, quantity: number) => {
    dispatch({ type: 'UPDATE_QUANTITY', payload: { id: productId, quantity } });
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