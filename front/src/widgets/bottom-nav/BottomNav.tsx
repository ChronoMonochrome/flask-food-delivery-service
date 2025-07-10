import React from 'react';
import { useDispatch } from 'react-redux';
import { 
  BottomNavigation, 
  BottomNavigationAction, 
  Paper, 
  Badge,
  Box 
} from '@mui/material';
import { 
  Home, 
  ShoppingCart, 
  Assignment 
} from '@mui/icons-material';
import { useNavigationSelector } from '../../features/navigation';
import { useBackendCartSelector } from '../../entities/cart';
import { navigationActions } from '../../features/navigation';
import { Page } from '../../shared/types';

export const BottomNav: React.FC = () => {
  const dispatch = useDispatch();
  const { currentPage } = useNavigationSelector();
  const { totalItems } = useBackendCartSelector();

  const handleNavigation = (page: Page) => {
    dispatch(navigationActions.navigateToPage(page));
  };

  const getPageIndex = (page: Page): number => {
    switch (page) {
      case 'home': return 0;
      case 'cart': return 1;
      case 'orders': return 2;
      default: return 0;
    }
  };

  return (
    <Paper 
      sx={{ 
        position: 'fixed', 
        bottom: 0, 
        left: 0, 
        right: 0, 
        zIndex: 1000,
        backgroundColor: 'background.paper',
        borderTop: '1px solid #4B5563',
      }} 
      elevation={3}
    >
      <BottomNavigation
        value={getPageIndex(currentPage)}
        sx={{
          backgroundColor: 'transparent',
          '& .MuiBottomNavigationAction-root': {
            color: 'text.secondary',
            '&.Mui-selected': {
              color: 'primary.main',
            },
          },
        }}
      >
        <BottomNavigationAction
          label="Главная"
          icon={<Home />}
          onClick={() => handleNavigation('home')}
        />
        <BottomNavigationAction
          label="Корзина"
          icon={
            <Badge badgeContent={totalItems} color="primary">
              <ShoppingCart />
            </Badge>
          }
          onClick={() => handleNavigation('cart')}
        />
        <BottomNavigationAction
          label="Заказы"
          icon={<Assignment />}
          onClick={() => handleNavigation('orders')}
        />
      </BottomNavigation>
    </Paper>
  );
};