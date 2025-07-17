import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { ArrowLeft, Phone, CreditCard, MessageSquare } from 'lucide-react';
import { LocationOn } from '@mui/icons-material';
import { useBackendCartSelector } from '../../entities/cart';
import { useClearCartMutation, useGetCartQuery } from '../../shared/api/cart-api';
import { navigationActions } from '../../features/navigation';
import { DeliveryInfo } from '../../shared/types';
import { LeafletMapPicker } from '../../components/YandexMapPicker/LeafletMapPicker';
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
} from '@mui/material';

export const CheckoutPage: React.FC = () => {
  const dispatch = useDispatch();
  const { totalItems, total } = useBackendCartSelector();
  const [clearCart] = useClearCartMutation();
  const { data: cartData } = useGetCartQuery();
  const [deliveryInfo, setDeliveryInfo] = useState<DeliveryInfo>({
    address: '',
    apartment: '',
    floor: '',
    phone: '',
    paymentMethod: 'cash',
    comment: ''
  });
  const [coordinates, setCoordinates] = useState<[number, number] | null>(null);
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deliveryCost, setDeliveryCost] = useState<number>(0);

  const handleBack = () => {
    dispatch(navigationActions.navigateToPage('cart'));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulate order processing
    await new Promise(resolve => setTimeout(resolve, 2000));

    await clearCart();
    dispatch(navigationActions.navigateToPage('success'));
    setIsSubmitting(false);
  };

  const handleAddressSelect = (address: string, coords: [number, number], cost: number) => {
    setDeliveryInfo({ ...deliveryInfo, address });
    setCoordinates(coords);
    setDeliveryCost(cost);
  };

  const isFormValid = deliveryInfo.address.length > 0 && deliveryInfo.phone.length > 0;

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
                >
                  <LocationOn sx={{ color: 'primary.main', mr: 1, width: "40px", height: "40px" }} />
                </IconButton>
              </Box>

              <Box display="flex" gap={2} alignItems="center" mt={2}>
                <TextField
                    value={deliveryInfo.apartment}
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
                    value={deliveryInfo.floor}
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
                value={deliveryInfo.comment}
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

          {/* Order Summary */}
          <Card sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" color="text.primary" mb={2}>
                Ваш заказ
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {cartData?.items.map((item, index) => (
                  <Box key={index}>
                    <Box display="flex" justifyContent="space-between">
                      <Typography color="text.secondary">
                      Товар {item.productId} × {item.quantity}
                      </Typography>
                      <Typography fontWeight="medium" color="text.primary">
                      ₽{/* TODO: Рассчитать цену товара */}
                      </Typography>
                    </Box>
                  {item.selectedAddons && item.selectedAddons.length > 0 && (
                      <Typography variant="body2" color="primary.main" sx={{ ml: 2 }}>
                        + {item.selectedAddons.length} добавок
                      </Typography>
                  )}
                  {item.selectedRecommendations && item.selectedRecommendations.length > 0 && (
                      <Typography variant="body2" color="success.main" sx={{ ml: 2 }}>
                        + {item.selectedRecommendations.length} дополнительно
                      </Typography>
                  )}
                  </Box>
              )) || (
                  <Typography color="text.secondary">Корзина пуста</Typography>
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
            disabled={!isFormValid || isSubmitting}
            variant="contained"
            size="large"
            fullWidth
            sx={{
              py: 2,
              borderRadius: 2,
              fontSize: '1.125rem',
              fontWeight: 'bold',
              background: isFormValid && !isSubmitting 
                ? 'linear-gradient(45deg, #EAB545 30%, #F59E0B 90%)'
                : undefined,
              '&:hover': {
                background: isFormValid && !isSubmitting 
                  ? 'linear-gradient(45deg, #F59E0B 30%, #EAB545 90%)'
                  : undefined,
              },
              '&:disabled': {
                backgroundColor: '#6B7280',
                color: '#9CA3AF',
              }
            }}
          >
            {isSubmitting ? 'Обрабатываем заказ...' : `Заказать на ₽${(total + deliveryCost).toLocaleString()}`}
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