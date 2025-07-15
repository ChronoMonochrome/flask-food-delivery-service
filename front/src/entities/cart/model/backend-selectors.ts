import { useSelector } from 'react-redux';
import { RootState } from '../../../app/store';

export const useBackendCartSelector = () => {
  return useSelector((state: RootState) => state.backendCart);
};

export const useProductQuantity = (productId: string) => {
  return useSelector((state: RootState) => 
    state.backendCart.productQuantities[productId] || 0
  );
};