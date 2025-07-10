import { useSelector } from 'react-redux';
import { RootState } from '../../../app/store';

export const useCartSelector = () => {
  return useSelector((state: RootState) => state.cart);
};