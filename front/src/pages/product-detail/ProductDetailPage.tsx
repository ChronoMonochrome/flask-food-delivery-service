import React, { useState } from 'react';
import { useCallback, useEffect, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import {
  Box,
  Container,
  Typography,
  Button,
  IconButton,
  Card,
  CardContent,
  Grid,
  Chip,
  Stack,
  FormControlLabel,
  Checkbox,
  ButtonGroup,
  AppBar,
  Toolbar
} from '@mui/material';
import { ArrowBack, Add, Remove, Check } from '@mui/icons-material';
import { useNavigationSelector } from '../../features/navigation';
import { useProductQuantity, useCartOperations } from '../../entities/cart';
import { navigationActions } from '../../features/navigation';
import { Addon, Recommendation } from '../../shared/types';

export const ProductDetailPage: React.FC = () => {
  const dispatch = useDispatch();
  const { selectedProduct } = useNavigationSelector();
  const cartOperations = useCartOperations();
  const { addToCart, updateQuantity } = cartOperations;
  
  const [selectedAddons, setSelectedAddons] = useState<Addon[]>([]);
  const [selectedRecommendations, setSelectedRecommendations] = useState<Recommendation[]>([]);
  const [addonQuantities, setAddonQuantities] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(false);

  // Получаем количество базового товара из кэша
  const currentQuantity = useProductQuantity(selectedProduct?.id || '');
  
  // Локальное состояние для отображения с защитой от мерцания
  const [displayQuantity, setDisplayQuantity] = useState(currentQuantity);
  const [isLocalUpdating, setIsLocalUpdating] = useState(false);

  // Синхронизируем только при реальных изменениях
  useEffect(() => {
    const shouldUpdate = !isLocalUpdating && 
      currentQuantity !== displayQuantity &&
      (currentQuantity > displayQuantity || displayQuantity === 0);
    
    if (shouldUpdate) {
      setDisplayQuantity(currentQuantity);
    }
  }, [currentQuantity, isLocalUpdating, displayQuantity]);

  if (!selectedProduct) {
    return null;
  }

  const handleAddonToggle = (addon: Addon) => {
    setSelectedAddons(prev => 
      prev.find(a => a.id === addon.id)
        ? prev.filter(a => a.id !== addon.id)
        : [...prev, addon]
    );
  };

  const handleRecommendationToggle = (recommendation: Recommendation) => {
    setSelectedRecommendations(prev => 
      prev.find(r => r.id === recommendation.id)
        ? prev.filter(r => r.id !== recommendation.id)
        : [...prev, recommendation]
    );
  };

  const handleAddonQuantityChange = (addonId: string, newQuantity: number) => {
    if (newQuantity <= 0) {
      setAddonQuantities(prev => {
        const updated = { ...prev };
        delete updated[addonId];
        return updated;
      });
      // Убираем из выбранных добавок
      setSelectedAddons(prev => prev.filter(a => a.id !== addonId));
    } else {
      setAddonQuantities(prev => ({
        ...prev,
        [addonId]: newQuantity
      }));
      // Добавляем в выбранные добавки если еще нет
      const addon = selectedProduct.availableAddons?.find(a => a.id === addonId);
      if (addon && !selectedAddons.find(a => a.id === addonId)) {
        setSelectedAddons(prev => [...prev, addon]);
      }
    }
  };

  const getAddonQuantity = (addonId: string): number => {
    return addonQuantities[addonId] || 0;
  };

  const handleAddToCart = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    setIsLocalUpdating(true);
    try {
      // Создаем добавки с количеством
      const addonsWithQuantity = selectedAddons.map(addon => ({
        ...addon,
        quantity: getAddonQuantity(addon.id)
      }));

      await addToCart(selectedProduct, addonsWithQuantity, selectedRecommendations);
      
      // Сбрасываем выбранные добавки и рекомендации после успешного добавления
      setSelectedAddons([]);
      setSelectedRecommendations([]);
      setAddonQuantities({});
    } catch (error) {
      console.error('Ошибка добавления товара в корзину:', error);
    } finally {
      setIsLoading(false);
      setIsLocalUpdating(false);
    }
  };

  const handleBaseProductQuantityChange = useCallback(async (newQuantity: number) => {
    if (isLoading) return;
    
    setIsLoading(true);
    setIsLocalUpdating(true);
    setDisplayQuantity(newQuantity); // Оптимистично обновляем
    
    try {
      // Для базового товара без добавок используем productId как itemId
      await updateQuantity(selectedProduct.id, selectedProduct.id, newQuantity);
    } catch (error) {
      console.error('Ошибка обновления количества:', error);
      // При ошибке возвращаем к исходному состоянию
      setDisplayQuantity(currentQuantity);
    } finally {
      setIsLoading(false);
      setIsLocalUpdating(false);
    }
  }, [selectedProduct.id, updateQuantity, isLoading, currentQuantity]);

  const handleBack = () => {
    dispatch(navigationActions.navigateToPage('home'));
  };

  const totalPrice = selectedProduct.price + 
    selectedAddons.reduce((sum, addon) => sum + (addon.price * getAddonQuantity(addon.id)), 0);

  // Мемоизируем состояние кнопок
  const buttonState = useMemo(() => ({
    showQuantityControls: displayQuantity > 0,
    isDisabled: isLoading || isLocalUpdating,
    canDecrease: displayQuantity > 0
  }), [displayQuantity, isLoading, isLocalUpdating]);
  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
      {/* Image */}
      <Box position="relative">
        <Box
          component="img"
          src={selectedProduct.image}
          alt={selectedProduct.name}
          sx={{
            width: '100%',
            height: { xs: 320, sm: 384, lg: '60vh' },
            maxHeight: 500,
            objectFit: 'cover',
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(to top, rgba(0,0,0,0.2), transparent)',
          }}
        />
        <IconButton
          onClick={handleBack}
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            backgroundColor: 'rgba(44, 44, 42, 0.9)',
            backdropFilter: 'blur(4px)',
            border: '1px solid #4B5563',
            '&:hover': { backgroundColor: 'rgba(44, 44, 42, 0.8)' },
          }}
        >
          <ArrowBack sx={{ color: 'white' }} />
        </IconButton>
      </Box>

      {/* Content */}
      <Card
        sx={{
          backgroundColor: 'background.paper',
          borderRadius: '24px 24px 0 0',
          mt: -3,
          position: 'relative',
          zIndex: 10,
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={3}>
            <Box>
              <Typography variant="h4" component="h1" fontWeight="bold" color="text.primary">
                {selectedProduct.name}
              </Typography>
              {selectedProduct.weight > 0 && (
                <Typography variant="body2" color="text.secondary">
                  Вес: {selectedProduct.weight}г
                </Typography>
              )}
            </Box>
            <Typography variant="h3" component="span" fontWeight="bold" color="primary.main">
              ₽{selectedProduct.price}
            </Typography>
          </Box>

          {selectedProduct.description && selectedProduct.description.trim() && (
            <Typography variant="h6" color="text.primary" sx={{ mb: 4, lineHeight: 1.6 }}>
              {selectedProduct.description}
            </Typography>
          )}

          {/* КБЖУ - компактная версия */}
          <Box 
            sx={{ 
              backgroundColor: 'rgba(58, 58, 55, 1)', 
              border: '1px solid #6B7280',
              borderRadius: 2,
              p: 2,
              mb: 4
            }}
          >
            <Typography variant="body2" fontWeight="medium" color="text.secondary" mb={1}>
              КБЖУ на 100г
            </Typography>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box textAlign="center">
                <Typography variant="body1" fontWeight="bold" color="primary.main">
                  {selectedProduct.nutrition.calories}
                </Typography>
                <Typography variant="caption" color="text.secondary">ккал</Typography>
              </Box>
              <Box textAlign="center">
                <Typography variant="body1" fontWeight="bold" color="info.main">
                  {selectedProduct.nutrition.protein}
                </Typography>
                <Typography variant="caption" color="text.secondary">белки</Typography>
              </Box>
              <Box textAlign="center">
                <Typography variant="body1" fontWeight="bold" color="warning.main">
                  {selectedProduct.nutrition.fat}
                </Typography>
                <Typography variant="caption" color="text.secondary">жиры</Typography>
              </Box>
              <Box textAlign="center">
                <Typography variant="body1" fontWeight="bold" color="success.main">
                  {selectedProduct.nutrition.carbs}
                </Typography>
                <Typography variant="caption" color="text.secondary">углеводы</Typography>
              </Box>
            </Box>
          </Box>

          {/* Состав */}
          {selectedProduct.ingredients && selectedProduct.ingredients.length > 0 && (
            <Box mb={4}>
              <Typography variant="h6" fontWeight="bold" color="text.primary" mb={2}>
                Состав:
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {selectedProduct.ingredients.map((ingredient, index) => (
                  <Chip
                    key={index}
                    label={ingredient}
                    sx={{
                      backgroundColor: 'rgba(58, 58, 55, 1)',
                      color: 'text.secondary',
                      border: '1px solid #6B7280',
                    }}
                  />
                ))}
              </Stack>
            </Box>
          )}

          {/* Добавки с выбором количества */}
          {selectedProduct.availableAddons && selectedProduct.availableAddons.length > 0 && (
            <Box mb={6}>
              <Typography variant="h6" fontWeight="bold" color="text.primary" mb={2}>
                Добавки:
              </Typography>
              <Grid container spacing={1.5}>
                {selectedProduct.availableAddons.map((addon) => {
                  const addonQuantity = getAddonQuantity(addon.id);
                  const isSelected = addonQuantity > 0;
                  
                  return (
                    <Grid item xs={6} sm={4} key={addon.id}>
                      <Card
                        onClick={() => handleAddonToggle(addon)}
                        sx={{
                          cursor: 'pointer',
                          p: 1.5,
                          borderRadius: 2,
                          border: isSelected ? '2px solid' : '1px solid #6B7280',
                          borderColor: isSelected ? 'primary.main' : '#6B7280',
                          backgroundColor: isSelected ? 'rgba(234, 181, 69, 0.1)' : 'rgba(58, 58, 55, 1)',
                          transition: 'all 0.2s ease',
                          '&:hover': {
                            backgroundColor: isSelected ? 'rgba(234, 181, 69, 0.2)' : 'rgba(107, 114, 128, 0.1)',
                            transform: 'scale(1.02)',
                          },
                        }}
                      >
                        <Box display="flex" flexDirection="column" alignItems="center" textAlign="center">
                          <Typography 
                            variant="body2" 
                            fontWeight="medium" 
                            color="text.primary"
                            sx={{ mb: 0.5, fontSize: '0.875rem' }}
                          >
                            {addon.name}
                          </Typography>
                          <Typography 
                            variant="caption" 
                            color="primary.main" 
                            fontWeight="bold"
                            sx={{ mb: 1 }}
                          >
                            ₽{addon.price}
                          </Typography>
                          
                          {/* Кнопки управления количеством */}
                          {addonQuantity === 0 ? (
                            <IconButton
                              onClick={(e) => {
                                e.stopPropagation();
                                handleAddonQuantityChange(addon.id, 1);
                              }}
                              size="small"
                              sx={{
                                backgroundColor: 'primary.main',
                                color: 'white',
                                width: 28,
                                height: 28,
                                '&:hover': { backgroundColor: 'secondary.main' },
                              }}
                            >
                              <Add fontSize="small" />
                            </IconButton>
                          ) : (
                            <Box display="flex" alignItems="center" gap={0.5}>
                              <IconButton
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleAddonQuantityChange(addon.id, addonQuantity - 1);
                                }}
                                size="small"
                                sx={{
                                  backgroundColor: 'rgba(58, 58, 55, 1)',
                                  border: '1px solid #6B7280',
                                  width: 24,
                                  height: 24,
                                  '&:hover': { backgroundColor: 'rgba(107, 114, 128, 0.1)' },
                                }}
                              >
                                <Remove sx={{ color: 'text.secondary', fontSize: '0.875rem' }} />
                              </IconButton>
                              <Typography 
                                variant="body2" 
                                fontWeight="bold" 
                                color="text.primary"
                                sx={{ minWidth: 20, textAlign: 'center' }}
                              >
                                {addonQuantity}
                              </Typography>
                              <IconButton
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleAddonQuantityChange(addon.id, addonQuantity + 1);
                                }}
                                size="small"
                                sx={{
                                  backgroundColor: 'primary.main',
                                  color: 'white',
                                  width: 24,
                                  height: 24,
                                  '&:hover': { backgroundColor: 'secondary.main' },
                                }}
                              >
                                <Add sx={{ color: 'white', fontSize: '0.875rem' }} />
                              </IconButton>
                            </Box>
                          )}
                        </Box>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>
            </Box>
          )}


          {/* Bottom Actions */}
          <Box
            sx={{
              position: 'sticky',
              bottom: 0,
              pt: 2,
              borderTop: '1px solid #4B5563',
              minHeight: 80, // Фиксированная высота для предотвращения мерцания
            }}
          >
            {/* Если есть базовый товар в корзине и нет выбранных добавок */}
            {buttonState.showQuantityControls && selectedAddons.length === 0 ? ( 
              <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ py: 1 }}>
                <ButtonGroup variant="outlined">
                  <IconButton
                    onClick={(e) => {
                      e.preventDefault();
                      handleBaseProductQuantityChange(displayQuantity - 1);
                    }}
                    disabled={buttonState.isDisabled || !buttonState.canDecrease}
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
                      border: '1px solid #6B7280',
                    }}
                  >
                    <Typography variant="h6" fontWeight="bold" color="text.primary">
                      {displayQuantity}
                    </Typography>
                  </Box>
                  <IconButton
                    onClick={(e) => {
                      e.preventDefault();
                      handleBaseProductQuantityChange(displayQuantity + 1);
                    }}
                    disabled={buttonState.isDisabled}
                    sx={{
                      backgroundColor: 'primary.main',
                      '&:hover': { backgroundColor: 'secondary.main' },
                    }}
                  >
                    <Add sx={{ color: 'white' }} />
                  </IconButton>
                </ButtonGroup>
                <Typography variant="h5" fontWeight="bold" color="text.primary">
                  ₽{(selectedProduct.price * displayQuantity).toLocaleString()}
                </Typography>
              </Box>
            ) : (
              /* Кнопка добавления в корзину */
              <Box sx={{ py: 1 }}>
                <Button
                  onClick={handleAddToCart}
                  disabled={buttonState.isDisabled}
                  variant="contained"
                  fullWidth
                  size="large"
                  sx={{ py: 2, borderRadius: 2, fontSize: '1.125rem', fontWeight: 'bold' }}
                >
                  {buttonState.isDisabled 
                    ? 'Добавляем...' 
                    : `Добавить в корзину - ₽${totalPrice.toLocaleString()}`
                  }
                </Button>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};