import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { useGetCartQuery } from '../../shared/api/cart-api';
import { useCartOperations } from '../../entities/cart';
import {
  Box,
  Container,
  Typography,
  Button,
  IconButton,
  Card,
  CardContent,
  AppBar,
  Toolbar,
  Stack,
  Chip,
  ButtonGroup,
  Collapse
} from '@mui/material';
import { 
  ArrowBack, 
  Add, 
  Remove, 
  Delete, 
  ShoppingBag,
  ExpandMore,
  ExpandLess
} from '@mui/icons-material';
import { useBackendCartSelector } from '../../entities/cart';
import { navigationActions } from '../../features/navigation';
import { BottomNav } from '../../widgets/bottom-nav/BottomNav';
import { LoadingSpinner } from '../../shared/ui/LoadingSpinner';
import { ErrorMessage } from '../../shared/ui/ErrorMessage';

export const CartPage: React.FC = () => {
  const dispatch = useDispatch();
  const { totalItems, total } = useBackendCartSelector();
  const { updateQuantity, removeFromCart } = useCartOperations();
  const [showRecommendations, setShowRecommendations] = useState(false);

  // Загружаем актуальную корзину при открытии страницы
  const { 
    data: cartData, 
    isLoading, 
    error,
    refetch 
  } = useGetCartQuery(undefined, {
    // Принудительно обновляем при входе на страницу
    refetchOnMountOrArgChange: true,
  });

  const handleBack = () => {
    dispatch(navigationActions.navigateToPage('home'));
  };

  const handleCheckout = () => {
    dispatch(navigationActions.navigateToPage('checkout'));
  };

  const handleUpdateQuantity = async (itemId: string, productId: string, quantity: number) => {
    await updateQuantity(itemId, productId, quantity);
  };

  const handleRemoveItem = async (itemId: string, productId: string) => {
    await removeFromCart(itemId, productId);
  };

  // Получаем все уникальные рекомендации из загруженной корзины
  // Получаем все уникальные рекомендации
  const getAllRecommendations = () => {
    if (!cartData?.items) return [];
    
    // TODO: Здесь нужно будет получить рекомендации из данных продуктов
    // Пока возвращаем пустой массив, так как в BackendCartItem нет информации о рекомендациях
    return [];
  };

  const handleAddRecommendation = async (recommendationId: string) => {
    // TODO: Реализовать добавление рекомендации через API
    console.log('Добавление рекомендации:', recommendationId);
  };

  if (isLoading) {
    return (
      <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default', display: 'flex', flexDirection: 'column' }}>
        <AppBar position="static" sx={{ backgroundColor: 'background.paper', boxShadow: 'none' }}>
          <Toolbar sx={{ borderBottom: '1px solid #4B5563' }}>
            <IconButton onClick={handleBack} sx={{ mr: 2 }}>
              <ArrowBack sx={{ color: 'text.secondary' }} />
            </IconButton>
            <Typography variant="h6" fontWeight="bold" color="text.primary">
              Корзина
            </Typography>
          </Toolbar>
        </AppBar>
        <LoadingSpinner />
        <BottomNav />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default', display: 'flex', flexDirection: 'column' }}>
        <AppBar position="static" sx={{ backgroundColor: 'background.paper', boxShadow: 'none' }}>
          <Toolbar sx={{ borderBottom: '1px solid #4B5563' }}>
            <IconButton onClick={handleBack} sx={{ mr: 2 }}>
              <ArrowBack sx={{ color: 'text.secondary' }} />
            </IconButton>
            <Typography variant="h6" fontWeight="bold" color="text.primary">
              Корзина
            </Typography>
          </Toolbar>
        </AppBar>
        <ErrorMessage message="Ошибка загрузки корзины" />
        <Button onClick={() => refetch()} variant="contained" sx={{ mx: 3, mt: 2 }}>
          Повторить
        </Button>
        <BottomNav />
      </Box>
    );
  }

  const items = cartData?.items || [];
  const recommendations = getAllRecommendations();

  if (items.length === 0) {
    return (
      <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default', display: 'flex', flexDirection: 'column' }}>
        <AppBar position="static" sx={{ backgroundColor: 'background.paper', boxShadow: 'none' }}>
          <Toolbar sx={{ borderBottom: '1px solid #4B5563' }}>
            <IconButton onClick={handleBack} sx={{ mr: 2 }}>
              <ArrowBack sx={{ color: 'text.secondary' }} />
            </IconButton>
            <Typography variant="h6" fontWeight="bold" color="text.primary">
              Корзина
            </Typography>
          </Toolbar>
        </AppBar>

        <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', px: 3, pb: 10 }}>
          <Box textAlign="center">
            <ShoppingBag sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h5" fontWeight="bold" color="text.primary" mb={1}>
              Корзина пуста
            </Typography>
            <Typography variant="body1" color="text.secondary" mb={4}>
              Добавьте товары из каталога
            </Typography>
            <Button
              onClick={handleBack}
              variant="contained"
              size="large"
              sx={{ px: 4, py: 1.5, borderRadius: 2, fontSize: '1rem', fontWeight: 'bold' }}
            >
              Перейти к покупкам
            </Button>
            <Typography variant="h4" fontWeight="bold" color="primary.main">₽{(total || 0).toLocaleString()}</Typography>
          </Box>
        </Box>

        <BottomNav />
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default', pb: 12 }}>
      <AppBar position="static" sx={{ backgroundColor: 'background.paper', boxShadow: 'none' }}>
        <Toolbar sx={{ borderBottom: '1px solid #4B5563' }}>
          <IconButton onClick={handleBack} sx={{ mr: 2 }}>
            <ArrowBack sx={{ color: 'text.secondary' }} />
          </IconButton>
          <Typography variant="h6" fontWeight="bold" color="text.primary" sx={{ flexGrow: 1 }}>
            Корзина
          </Typography>
          <Chip 
            label={`${totalItems} товар(ов)`}
            sx={{ backgroundColor: 'primary.main', color: 'white', fontWeight: 'medium' }}
          />
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 2 }}>
        <Stack spacing={2}>
          {items.map((item) => {
            return (
                <Card key={item.id} sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
                  <CardContent>
                    {/* TODO: Здесь нужно будет получить данные продукта по productId */}
                    <Box display="flex" alignItems="center" gap={2}>
                      <Box
                          component="img"
                          src={item.image || "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200"}
                          alt="Товар"
                          sx={{ width: 64, height: 64, borderRadius: 3, objectFit: 'cover' }}
                      />
                      <Box flexGrow={1}>
                        <Typography variant="h6" fontWeight="bold" color="text.primary">
                          {item.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Количество: {item.quantity}
                        </Typography>

                        {/* Кастомный WOK */}
                        {item.customWok && (
                            <Box mt={1}>
                              <Typography variant="caption" color="primary.main">
                                Кастомный WOK
                              </Typography>
                            </Box>
                        )}

                        {/* Допы */}
                        {item.selectedAddons && item.selectedAddons.length > 0 && (
                            <Box mt={1} >
                              <Typography variant="caption" color="primary.main">
                                Добавки: {item.selectedAddons.length} шт. {" "}
                              </Typography>
                              {item.selectedAddons.map((addon) => (
                                  <Typography key={addon.id} variant="caption" color="primary.main">
                                    {addon.group_name} кол-во: {addon.quantity}, {" "}
                                  </Typography>
                              ))}
                            </Box>
                        )}

                        {/*/!* Рекомендации *!/*/}
                        {/*{item.selectedRecommendations && item.selectedRecommendations.length > 0 && (*/}
                        {/*  <Typography variant="caption" color="success.main" display="block">*/}
                        {/*    Дополнительно: {item.selectedRecommendations.length} шт.*/}
                        {/*  </Typography>*/}
                        {/*)}*/}

                        <Typography variant="h6" fontWeight="bold" color="primary.main" mt={1}>
                          {item.priceTotal}₽
                        </Typography>
                      </Box>
                      <IconButton
                          onClick={() => handleRemoveItem(item.id, item.productId)}
                          sx={{ color: 'error.main', '&:hover': { backgroundColor: 'rgba(239, 68, 68, 0.1)' } }}
                      >
                        <Delete />
                      </IconButton>
                    </Box>

                    <Box display="flex" justifyContent="space-between" alignItems="center" mt={2}>
                      <ButtonGroup variant="outlined">
                        <IconButton
                            onClick={() => handleUpdateQuantity(item.id, item.productId, item.quantity - 1)}
                            sx={{
                              backgroundColor: 'rgba(58, 58, 55, 1)',
                              border: '1px solid #6B7280',
                              '&:hover': { backgroundColor: 'rgba(107, 114, 128, 0.1)' },
                            }}
                        >
                          <Remove sx={{ color: 'text.secondary' }} />
                        </IconButton>
                        <Box
                            display="flex"
                            alignItems="center"
                            justifyContent="center"
                            sx={{
                              minWidth: 60,
                              backgroundColor: 'background.paper',
                              borderRadius: "10px",
                              mx: 1
                            }}
                        >
                          <Typography variant="h6" fontWeight="bold" color="text.primary">
                            {item.quantity}
                          </Typography>
                        </Box>
                        <IconButton
                            onClick={() => handleUpdateQuantity(item.id, item.productId, item.quantity + 1)}
                            sx={{
                              backgroundColor: 'primary.main',
                              '&:hover': { backgroundColor: 'secondary.main' },
                            }}
                        >
                          <Add sx={{ color: 'white' }} />
                        </IconButton>
                      </ButtonGroup>
                      <Typography variant="h6" fontWeight="bold" color="text.primary">
                        ₽{/* TODO: Рассчитать общую стоимость */}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
            );
          })}

          {/* Рекомендации */}
          {recommendations.length > 0 && (
            <Card sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6" fontWeight="bold" color="text.primary">
                    Отлично дополнит ваш заказ
                  </Typography>
                  <IconButton
                    onClick={() => setShowRecommendations(!showRecommendations)}
                    sx={{ color: 'primary.main' }}
                  >
                    {showRecommendations ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                </Box>
                
                <Collapse in={showRecommendations}>
                  <Stack spacing={2}>
                    {recommendations.map((recommendation) => (
                      <Box
                        key={recommendation.id}
                        display="flex"
                        justifyContent="space-between"
                        alignItems="center"
                        sx={{
                          p: 2,
                          backgroundColor: 'rgba(58, 58, 55, 1)',
                          borderRadius: 3,
                          border: '1px solid #6B7280',
                          '&:hover': { backgroundColor: 'rgba(107, 114, 128, 0.1)' },
                        }}
                      >
                        <Box display="flex" alignItems="center" gap={2}>
                          <Box
                            component="img"
                            src={recommendation.image}
                            alt={recommendation.name}
                            sx={{ width: 48, height: 48, borderRadius: 2, objectFit: 'cover' }}
                          />
                          <Box>
                            <Typography fontWeight="medium" color="text.primary">{recommendation.name}</Typography>
                            <Typography variant="body2" color="primary.main">₽{recommendation.price}</Typography>
                          </Box>
                        </Box>
                        <IconButton
                          onClick={() => handleAddRecommendation(recommendation.id)}
                          sx={{
                            backgroundColor: 'primary.main',
                            color: 'white',
                            '&:hover': { backgroundColor: 'secondary.main' },
                          }}
                        >
                          <Add />
                        </IconButton>
                      </Box>
                    ))}
                  </Stack>
                </Collapse>
              </CardContent>
            </Card>
          )}
          
          {/* Отступ для кнопки оформления заказа */}
          <Box sx={{ height: 120 }} />
        </Stack>
      </Container>

      {/* Bottom Actions */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 72, // Отступ от BottomNav
          left: 0,
          right: 0,
          backgroundColor: 'background.paper',
          p: 2,
          borderTop: '1px solid #4B5563',
          boxShadow: 3,
        }}
      >
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" fontWeight="bold" color="text.primary">Итого:</Typography>
          <Typography variant="h4" fontWeight="bold" color="primary.main">₽{total.toLocaleString()}</Typography>
        </Box>
        <Button
          onClick={handleCheckout}
          variant="contained"
          fullWidth
          size="large"
          sx={{ py: 2, borderRadius: 2, fontSize: '1.125rem', fontWeight: 'bold' }}
        >
          Оформить заказ
        </Button>
      </Box>

      <BottomNav />
    </Box>
  );
};