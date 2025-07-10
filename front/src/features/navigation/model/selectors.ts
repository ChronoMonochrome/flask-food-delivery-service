import { useSelector } from 'react-redux';
import { RootState } from '../../../app/store';

export const useNavigationSelector = () => {
  return useSelector((state: RootState) => state.navigation);
};