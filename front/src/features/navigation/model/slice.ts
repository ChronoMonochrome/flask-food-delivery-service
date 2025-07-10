import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Page, Product } from '../../../shared/types';

interface NavigationState {
  currentPage: Page;
  selectedProduct: Product | null;
}

const initialState: NavigationState = {
  currentPage: 'home',
  selectedProduct: null,
};

export const navigationSlice = createSlice({
  name: 'navigation',
  initialState,
  reducers: {
    setCurrentPage: (state, action: PayloadAction<Page>) => {
      state.currentPage = action.payload;
    },
    setSelectedProduct: (state, action: PayloadAction<Product | null>) => {
      state.selectedProduct = action.payload;
    },
    navigateToProduct: (state, action: PayloadAction<Product>) => {
      state.selectedProduct = action.payload;
      state.currentPage = action.payload.isCustomizable ? 'wok-builder' : 'product';
    },
    navigateToPage: (state, action: PayloadAction<Page>) => {
      state.currentPage = action.payload;
      if (action.payload === 'home') {
        state.selectedProduct = null;
      }
    },
  },
});

export const navigationActions = navigationSlice.actions;