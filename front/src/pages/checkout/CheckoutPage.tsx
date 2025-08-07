// front/src/pages/checkout/CheckoutPage.tsx

import React, { useState, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { ArrowLeft, Phone, CreditCard, MessageSquare } from 'lucide-react';
import { LocationOn } from '@mui/icons-material';
import { useBackendCartSelector } from '../../entities/cart';
import { useClearCartMutation, useGetCartQuery } from '../../shared/api/cart-api';
import { navigationActions } from '../../features/navigation';
import { DeliveryInfo, Order } from '../../types/api'; // Ensure correct imports for your types
import { LeafletMapPicker } from '../../components/YandexMapPicker/LeafletMapPicker';
import { useCreateOrderMutation, useGetOrderStatusQuery } from '../../store/api';
import {
  Box,
  Container,
  Typography,
  Button,
  IconButton,
  Card,
  CardContent,
  TextField,
  FormControl,
  RadioGroup,
  FormControlLabel,
  Radio,
  CircularProgress,
} from '@mui/material';

export const CheckoutPage: React.FC = () => {
  const dispatch = useDispatch();
  const { totalItems, total } = useBackendCartSelector();
  const [clearCart] = useClearCartMutation();
  const { data: cartData, isSuccess: isCartDataLoaded, isLoading: isCartLoading, isError: isCartError } = useGetCartQuery();

  const [deliveryInfo, setDeliveryInfo] = useState<DeliveryInfo>({
    address: '',
    apartment: null,
    floor: null,
    phone: '',
    paymentMethod: 'cash',
    comment: null
  });
  const [coordinates, setCoordinates] = useState<[number, number] | null>(null);
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deliveryCost, setDeliveryCost] = useState<number>(0);
  const [createOrder, { isLoading: isCreatingOrder }] = useCreateOrderMutation();
  const [orderIdForPolling, setOrderIdForPolling] = useState<string | null>(null);

  const { data: orderStatusData, refetch: refetchOrderStatus } = useGetOrderStatusQuery(
    orderIdForPolling!,
    {
      pollingInterval: orderIdForPolling && deliveryInfo.paymentMethod === 'online' ? 3000 : 0,
      skip: !orderIdForPolling || deliveryInfo.paymentMethod !== 'online',
    }
  );

  useEffect(() => {
    if (orderStatusData && orderIdForPolling && deliveryInfo.paymentMethod === 'online') {
      if (orderStatusData.status === 'paid' || orderStatusData.status === 'completed') {
        // Clear cart after successful online payment completion
        clearCart();
        dispatch(navigationActions.navigateToPage('success'));
        setIsSubmitting(false);
        setOrderIdForPolling(null);
      }
    }
  }, [orderStatusData, orderIdForPolling, deliveryInfo.paymentMethod, clearCart, dispatch]);


  const handleBack = () => {
    dispatch(navigationActions.navigateToPage('cart'));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    if (!cartData || cartData.items.length === 0) {
      alert('Your cart is empty!');
      setIsSubmitting(false);
      return;
    }

    try {
      const orderPayload = {
          address: deliveryInfo.address,
          apartment: deliveryInfo.apartment || null,
          floor: deliveryInfo.floor || null,
          phone: deliveryInfo.phone,
          comment: deliveryInfo.comment || null,
          latitude: coordinates ? coordinates[0] : null,
          longitude: coordinates ? coordinates[1] : null,
          paymentMethod: deliveryInfo.paymentMethod,
      };

      // The 'response' object will now correctly contain 'paymentUrl' and 'yookassaPaymentId'
      // because the backend's order_model has been updated.
      const response = await createOrder(orderPayload).unwrap();
      const { orderId, paymentUrl } = response; // Destructure paymentUrl directly

      if (deliveryInfo.paymentMethod === 'online' && paymentUrl) {
        window.location.href = paymentUrl; // Redirect to Yookassa
        setOrderIdForPolling(orderId); // Start polling for status
      } else {
        // For cash/card payments, clear cart immediately and navigate to success
        await clearCart(); // Uncommented this line to clear cart for non-online payments
        dispatch(navigationActions.navigateToPage('success'));
        setIsSubmitting(false);
      }
    } catch (error) {
      console.error('Failed to place order:', error);
      alert('Failed to place order. Please try again.');
      setIsSubmitting(false);
    }
  };

  const handleAddressSelect = (address: string, coords: [number, number], cost: number) => {
    setDeliveryInfo({ ...deliveryInfo, address });
    setCoordinates(coords);
    setDeliveryCost(cost);
    setIsMapOpen(false);
  };

  const isFormValid = deliveryInfo.address.length > 0 && deliveryInfo.phone.length > 0;
  const submitButtonText = isSubmitting
    ? (deliveryInfo.paymentMethod === 'online' ? 'Перенаправляем на оплату...' : 'Обрабатываем заказ...')
    : `Заказать на ₽${(total + deliveryCost).toLocaleString()}`; // Keep total for display, but not sent in payload

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
      {/* Header */}
      <Box sx={{ backgroundColor: 'background.paper', borderBottom: '1px solid #4B5563' }}>
        <Box display="flex" alignItems="center" p={2}>
          <IconButton onClick={handleBack} sx={{ mr: 2, color: 'text.secondary' }}>
            <ArrowLeft size={24} />
          </IconButton>
          <Typography variant="h6" fontWeight="bold" color="text.primary">
            Оформление заказа
          </Typography>
        </Box>
      </Box>

      <Container maxWidth="md" sx={{ py: 3 }}>
        <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Address */}
          <Card sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <LocationOn sx={{ color: 'primary.main', mr: 1 }} />
                <Typography variant="h6" fontWeight="bold" color="text.primary">
                  Адрес доставки
                </Typography>
              </Box>

              <Box display="flex" gap={2} alignItems="center">
                <TextField
                  value={deliveryInfo.address}
                  placeholder="Выберите адрес на карте"
                  variant="outlined"
                  required
                  fullWidth
                  InputProps={{
                    readOnly: true,
                    sx: {
                      backgroundColor: 'rgba(58, 58, 55, 1)',
                      border: '1px solid #6B7280',
                      borderRadius: 2,
                      color: 'text.primary',
                      '& input': { color: 'text.primary' },
                      '&:hover': { borderColor: 'primary.main' },
                    }
                  }}
                />
                <IconButton
                  onClick={() => setIsMapOpen(true)}
                  sx={{ p: 0 }}
                >
                  <LocationOn sx={{ color: 'primary.main', mr: 1, width: "40px", height: "40px" }} />
                </IconButton>
              </Box>

              <Box display="flex" gap={2} alignItems="center" mt={2}>
                <TextField
                  value={deliveryInfo.apartment || ''}
                  onChange={(e) => setDeliveryInfo({ ...deliveryInfo, apartment: e.target.value })}
                  placeholder="Квартира"
                  variant="outlined"
                  fullWidth
                  InputProps={{
                    sx: {
                      backgroundColor: 'rgba(58, 58, 55, 1)',
                      border: '1px solid #6B7280',
                      borderRadius: 2,
                      color: 'text.primary',
                      '& input': { color: 'text.primary' },
                      '&:hover': { borderColor: 'primary.main' },
                    }
                  }}
                />
                <TextField
                  value={deliveryInfo.floor || ''}
                  onChange={(e) => setDeliveryInfo({ ...deliveryInfo, floor: e.target.value })}
                  placeholder="Этаж"
                  variant="outlined"
                  fullWidth
                  InputProps={{
                    sx: {
                      backgroundColor: 'rgba(58, 58, 55, 1)',
                      border: '1px solid #6B7280',
                      borderRadius: 2,
                      color: 'text.primary',
                      '& input': { color: 'text.primary' },
                      '&:hover': { borderColor: 'primary.main' },
                    }
                  }}
                />
              </Box>

              {coordinates && (
                <Typography variant="caption" color="text.secondary" mt={1} display="block">
                  Координаты: {coordinates[0].toFixed(6)}, {coordinates[1].toFixed(6)}
                  {deliveryCost > 0 && (
                    <span style={{ marginLeft: 16, color: '#EAB545' }}>
                      Стоимость доставки: ₽{deliveryCost}
                    </span>
                  )}
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Phone */}
          <Card sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Phone sx={{ color: 'primary.main', mr: 1 }} />
                <Typography variant="h6" fontWeight="bold" color="text.primary">
                  Номер телефона
                </Typography>
              </Box>
              <TextField
                type="tel"
                value={deliveryInfo.phone}
                onChange={(e) => setDeliveryInfo({ ...deliveryInfo, phone: e.target.value })}
                placeholder="+7 (999) 999-99-99"
                required
                fullWidth
                InputProps={{
                  sx: {
                    backgroundColor: 'rgba(58, 58, 55, 1)',
                    border: '1px solid #6B7280',
                    borderRadius: 2,
                    color: 'text.primary',
                    '& input': { color: 'text.primary' },
                    '&:hover': { borderColor: 'primary.main' },
                  }
                }}
              />
            </CardContent>
          </Card>

          {/* Payment Method */}
          <Card sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <CreditCard sx={{ color: 'primary.main', mr: 1 }} />
                <Typography variant="h6" fontWeight="bold" color="text.primary">
                  Способ оплаты
                </Typography>
              </Box>
              <FormControl component="fieldset">
                <RadioGroup
                  value={deliveryInfo.paymentMethod}
                  onChange={(e) => setDeliveryInfo({ ...deliveryInfo, paymentMethod: e.target.value as any })}
                >
                  {[
                    { value: 'cash', label: 'Наличными курьеру' },
                    { value: 'card', label: 'Картой курьеру' },
                    { value: 'online', label: 'Онлайн оплата' }
                  ].map((option) => (
                    <FormControlLabel
                      key={option.value}
                      value={option.value}
                      control={<Radio sx={{ color: 'primary.main' }} />}
                      label={<Typography color="text.primary">{option.label}</Typography>}
                    />
                  ))}
                </RadioGroup>
              </FormControl>
            </CardContent>
          </Card>

          {/* Comment */}
          <Card sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <MessageSquare sx={{ color: 'primary.main', mr: 1 }} />
                <Typography variant="h6" fontWeight="bold" color="text.primary">
                  Комментарий к заказу
                </Typography>
              </Box>
              <TextField
                value={deliveryInfo.comment || ''}
                onChange={(e) => setDeliveryInfo({ ...deliveryInfo, comment: e.target.value })}
                placeholder="Дополнительные пожелания..."
                multiline
                rows={3}
                fullWidth
                InputProps={{
                  sx: {
                    backgroundColor: 'rgba(58, 58, 55, 1)',
                    border: '1px solid #6B7280',
                    borderRadius: 2,
                    color: 'text.primary',
                    '& textarea': { color: 'text.primary' },
                    '&:hover': { borderColor: 'primary.main' },
                  }
                }}
              />
            </CardContent>
          </Card>

          {/* Order Summary (Display only - not part of payload sent) */}
          <Card sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" color="text.primary" mb={2}>
                Ваш заказ
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {isCartLoading && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                    <CircularProgress />
                  </Box>
                )}
                {isCartError && (
                  <Typography color="error" sx={{ textAlign: 'center' }}>
                    Не удалось загрузить данные корзины.
                  </Typography>
                )}
                {isCartDataLoaded && cartData?.items?.length === 0 && (
                  <Typography color="text.secondary">Корзина пуста</Typography>
                )}
                {isCartDataLoaded && cartData?.items && cartData.items.length > 0 && (
                  cartData.items.map((item, index) => (
                    <Box key={item.id || index}>
                      <Box display="flex" justifyContent="space-between">
                        <Typography color="text.secondary">
                          {item.productId} × {item.quantity}
                        </Typography>
                      </Box>
                      {item.selectedAddons && item.selectedAddons.length > 0 && (
                        <Typography variant="body2" color="primary.main" sx={{ ml: 2 }}>
                          + {item.selectedAddons.map(addon => `${addon.id} (x${addon.quantity})`).join(', ')}
                        </Typography>
                      )}
                      {item.selectedRecommendations && item.selectedRecommendations.length > 0 && (
                        <Typography variant="body2" color="success.main" sx={{ ml: 2 }}>
                          + {item.selectedRecommendations.map(recId => recId).join(', ')}
                        </Typography>
                      )}
                    </Box>
                  ))
                )}
                <Box sx={{ borderTop: '1px solid #4B5563', pt: 2, mt: 2 }}>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">Товары:</Typography>
                    <Typography variant="body2" fontWeight="medium" color="text.primary">₽{total.toLocaleString()}</Typography>
                  </Box>
                  {deliveryCost > 0 && (
                    <Box display="flex" justifyContent="space-between" mt={1}>
                      <Typography variant="body2" color="text.secondary">Доставка:</Typography>
                      <Typography variant="body2" fontWeight="medium" color="text.primary">₽{deliveryCost.toLocaleString()}</Typography>
                    </Box>
                  )}
                  <Box display="flex" justifyContent="space-between" mt={1}>
                    <Typography variant="h6" fontWeight="bold" color="text.primary">Итого:</Typography>
                    <Typography variant="h6" fontWeight="bold" color="primary.main">₽{(total + deliveryCost).toLocaleString()}</Typography>
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>

          <Button
            type="submit"
            disabled={!isFormValid || isSubmitting || !isCartDataLoaded || isCreatingOrder}
            variant="contained"
            size="large"
            fullWidth
            sx={{
              py: 2,
              borderRadius: 2,
              fontSize: '1.125rem',
              fontWeight: 'bold',
              background: isFormValid && !isSubmitting && !isCreatingOrder
                ? 'linear-gradient(45deg, #EAB545 30%, #F59E0B 90%)'
                : undefined,
              '&:hover': {
                background: isFormValid && !isSubmitting && !isCreatingOrder
                  ? 'linear-gradient(45deg, #F59E0B 30%, #EAB545 90%)'
                  : undefined,
              },
              '&:disabled': {
                backgroundColor: '#6B7280',
                color: '#9CA3AF',
              }
            }}
          >
            {isSubmitting || isCreatingOrder ? <CircularProgress size={24} color="inherit" /> : submitButtonText}
          </Button>
        </Box>
      </Container>

      {/* Yandex Map Picker */}
      <LeafletMapPicker
        open={isMapOpen}
        onClose={() => setIsMapOpen(false)}
        onAddressSelect={handleAddressSelect}
      />
    </Box>
  );
};
