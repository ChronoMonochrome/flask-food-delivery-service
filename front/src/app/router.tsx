import React from 'react';
import { useSelector } from 'react-redux';
import { RootState } from './store';
import { HomePage } from '../pages/home/HomePage';
import { ProductDetailPage } from '../pages/product-detail/ProductDetailPage';
import { WokBuilderPage } from '../pages/wok-builder/WokBuilderPage';
import { CartPage } from '../pages/cart/CartPage';
import { CheckoutPage } from '../pages/checkout/CheckoutPage';
import { OrderSuccessPage } from '../pages/order-success/OrderSuccessPage';
import { MyOrdersPage } from '../pages/my-orders/MyOrdersPage';

export const AppRouter: React.FC = () => {
  const currentPage = useSelector((state: RootState) => state.navigation.currentPage);

  switch (currentPage) {
    case 'home':
      return <HomePage />;
    case 'product':
      return <ProductDetailPage />;
    case 'wok-builder':
      return <WokBuilderPage />;
    case 'cart':
      return <CartPage />;
    case 'checkout':
      return <CheckoutPage />;
    case 'success':
      return <OrderSuccessPage />;
    case 'orders':
      return <MyOrdersPage />;
    default:
      return <HomePage />;
  }
};