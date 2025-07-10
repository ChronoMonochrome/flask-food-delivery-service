import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import {
  Box,
  Container,
  Typography,
  Button,
  TextField,
  Card,
  CardContent,
  AppBar,
  Toolbar,
  IconButton,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Stack
} from '@mui/material';
import { ArrowBack, LocationOn, Phone, CreditCard, Message } from '@mui/icons-material';
import { useCartSelector, cartActions } from '../../entities/cart';
import { navigationActions } from '../../features/navigation';
import { DeliveryInfo } from '../../shared/types';

export const CheckoutPage: React.FC = () => {
  const dispatch = useDispatch();
  const { items, total } = useCartSelector();
  const [deliveryInfo, setDeliveryInfo] = useState<DeliveryInfo>({
    address: '',
    phone: '',
    paymentMethod: 'cash',
    comment: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleBack = () => {
    dispatch(navigationActions.navigateToPage('cart'));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulate order processing
    await new Promise(resolve => setTimeout(resolve, 2000));

    dispatch(cartActions.clearCart());
    dispatch(navigationActions.navigateToPage('success'));
    setIsSubmitting(false);
  };

  const isFormValid = deliveryInfo.address.length > 0 && deliveryInfo.phone.length > 0;

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
      <AppBar position="static" sx={{ backgroundColor: 'background.paper', boxShadow: 'none' }}>
        <Toolbar sx={{ borderBottom: '1px solid #4B5563' }}>
          <IconButton onClick={handleBack} sx={{ mr: 2 }}>
            <ArrowBack sx={{ color: 'text.secondary' }} />
          </IconButton>
          <Typography variant="h6" fontWeight="bold" color="text.primary">
            Оформление заказа
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 3 }}>
        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
            {/* Address */}
            <Card sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <LocationOn sx={{ color: 'primary.main', mr: 1 }} />
                  <Typography variant="h6" fontWeight="bold" color="text.primary">
                    Адрес доставки
                  </Typography>
                </Box>
                <TextField
                  fullWidth
                  value={deliveryInfo.address}
                  onChange={(e) => setDeliveryInfo({ ...deliveryInfo, address: e.target.value })}
                  placeholder="Введите адрес доставки"
                  required
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: '#374151',
                      '& fieldset': { borderColor: '#4B5563' },
                      '&:hover fieldset': { borderColor: '#6B7280' },
                      '&.Mui-focused fieldset': { borderColor: 'primary.main' },
                    },
                  }}
                />
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
                  fullWidth
                  type="tel"
                  value={deliveryInfo.phone}
                  onChange={(e) => setDeliveryInfo({ ...deliveryInfo, phone: e.target.value })}
                  placeholder="+7 (999) 999-99-99"
                  required
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: '#374151',
                      '& fieldset': { borderColor: '#4B5563' },
                      '&:hover fieldset': { borderColor: '#6B7280' },
                      '&.Mui-focused fieldset': { borderColor: 'primary.main' },
                    },
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
                <FormControl>
                  <RadioGroup
                    value={deliveryInfo.paymentMethod}
                    onChange={(e) => setDeliveryInfo({ ...deliveryInfo, paymentMethod: e.target.value as any })}
                  >
                    <FormControlLabel 
                      value="cash" 
                      control={<Radio sx={{ color: 'primary.main' }} />} 
                      label={<Typography color="text.secondary">Наличными курьеру</Typography>}
                    />
                    <FormControlLabel 
                      value="card" 
                      control={<Radio sx={{ color: 'primary.main' }} />} 
                      label={<Typography color="text.secondary">Картой курьеру</Typography>}
                    />
                    <FormControlLabel 
                      value="online" 
                      control={<Radio sx={{ color: 'primary.main' }} />} 
                      label={<Typography color="text.secondary">Онлайн оплата</Typography>}
                    />
                  </RadioGroup>
                </FormControl>
              </CardContent>
            </Card>

            {/* Comment */}
            <Card sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Message sx={{ color: 'primary.main', mr: 1 }} />
                  <Typography variant="h6" fontWeight="bold" color="text.primary">
                    Комментарий к заказу
                  </Typography>
                </Box>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  value={deliveryInfo.comment}
                  onChange={(e) => setDeliveryInfo({ ...deliveryInfo, comment: e.target.value })}
                  placeholder="Дополнительные пожелания..."
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: '#374151',
                      '& fieldset': { borderColor: '#4B5563' },
                      '&:hover fieldset': { borderColor: '#6B7280' },
                      '&.Mui-focused fieldset': { borderColor: 'primary.main' },
                    },
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
                <Stack spacing={1}>
                  {items.map((item, index) => (
                    <Box key={index}>
                      <Box display="flex" justifyContent="space-between">
                        <Typography variant="body2" color="text.secondary">
                          {item.product.name} × {item.quantity}
                        </Typography>
                        <Typography variant="body2" fontWeight="medium" color="text.primary">
                          ₽{((item.product.price + 
                            item.selectedAddons.reduce((sum, addon) => sum + (addon.price * (addon.quantity || 1)), 0) +
                            (!item.customWok ? item.selectedRecommendations.reduce((sum, rec) => sum + rec.price, 0) : 0)
                          ) * item.quantity).toLocaleString()}
                        </Typography>
                      </Box>
                      {item.selectedAddons.length > 0 && (
                        <Typography variant="caption" color="primary.main" sx={{ ml: 1, display: 'block' }}>
                          + {item.selectedAddons.map(addon => 
                            `${addon.name}${addon.quantity && addon.quantity > 1 ? ` x${addon.quantity}` : ''}`
                          ).join(', ')}
                        </Typography>
                      )}
                      {item.selectedRecommendations.length > 0 && (
                        <Typography variant="caption" color="success.main" sx={{ ml: 1, display: 'block' }}>
                          + {item.selectedRecommendations.map(rec => rec.name).join(', ')}
                        </Typography>
                      )}
                    </Box>
                  ))}
                  <Box sx={{ borderTop: '1px solid #4B5563', pt: 1, mt: 2 }}>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="h6" fontWeight="bold" color="text.primary">Итого:</Typography>
                      <Typography variant="h6" fontWeight="bold" color="primary.main">₽{total.toLocaleString()}</Typography>
                    </Box>
                  </Box>
                </Stack>
              </CardContent>
            </Card>

            <Button
              type="submit"
              disabled={!isFormValid || isSubmitting}
              variant="contained"
              size="large"
              sx={{
                py: 2,
                borderRadius: 2,
                fontSize: '1.125rem',
                fontWeight: 'bold',
                opacity: isFormValid && !isSubmitting ? 1 : 0.5,
              }}
            >
              {isSubmitting ? 'Обрабатываем заказ...' : `Заказать на ₽${total.toLocaleString()}`}
            </Button>
          </Stack>
        </form>
      </Container>
    </Box>
  );
};