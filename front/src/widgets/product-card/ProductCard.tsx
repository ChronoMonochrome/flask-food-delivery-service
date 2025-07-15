import React from 'react';
import { useDispatch } from 'react-redux';
import {
  Card,
  CardMedia,
  CardContent,
  Typography,
  IconButton,
  Box,
  Chip,
  ButtonGroup,
  Button
} from '@mui/material';
import { Add, Remove } from '@mui/icons-material';
import { Product } from '../../shared/types';
import { useProductQuantity, useCartOperations } from '../../entities/cart';
import { navigationActions } from '../../features/navigation';

interface ProductCardProps {
  product: Product;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const dispatch = useDispatch();
  const currentQuantity = useProductQuantity(product.id);
  const { addToCart, updateQuantity } = useCartOperations();

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (product.isCustomizable) {
      dispatch(navigationActions.navigateToProduct(product));
      return;
    }
    
    addToCart(product, [], []);
  };

  const handleQuantityChange = async (e: React.MouseEvent, newQuantity: number) => {
    e.stopPropagation();
    
    if (product.isCustomizable) {
      dispatch(navigationActions.navigateToProduct(product));
      return;
    }
    
    // Для простых товаров без добавок используем базовый itemId = productId
    await updateQuantity(product.id, product.id, newQuantity);
  };

  const handleCardClick = () => {
    dispatch(navigationActions.navigateToProduct(product));
  };

  return (
    <Card
      onClick={handleCardClick}
      sx={{
        width: '100%',
        maxWidth: { xs: 320, sm: 300, md: 280 }, // Адаптивная ширина
        height: { xs: 440, sm: 420 }, // Адаптивная высота
        display: 'flex',
        flexDirection: 'column',
        cursor: 'pointer',
        transition: 'all 0.3s ease',
        backgroundColor: 'background.paper',
        border: '1px solid #4B5563',
        borderRadius: 2.5, // Немного увеличенные скругления для карточек
        overflow: 'hidden',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 8px 25px rgba(0, 0, 0, 0.15)',
          borderColor: 'primary.main',
        },
      }}
    >
      {/* Контейнер изображения - адаптивный */}
      <Box 
        sx={{ 
          position: 'relative',
          width: '100%',
          height: { xs: 200, sm: 180 }, // Адаптивная высота изображения
          flexShrink: 0,
          overflow: 'hidden',
          backgroundColor: '#374151'
        }}
      >
        <CardMedia
          component="img"
          image={product.image || 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=400'}
          alt={product.name || 'Товар'}
          sx={{ 
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transition: 'transform 0.3s ease',
          }}
          onError={(e) => {
            e.currentTarget.src = 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=400';
          }}
        />
        
        {/* Кнопка добавления или управления количеством */}
        {currentQuantity === 0 ? (
          <IconButton
            onClick={handleAddToCart}
            sx={{
              position: 'absolute',
              bottom: 12,
              right: 12,
              background: 'linear-gradient(45deg, #EAB545 30%, #F59E0B 90%)',
              color: 'white',
              width: 40,
              height: 40,
              boxShadow: '0 4px 12px rgba(234, 181, 69, 0.4)',
              '&:hover': {
                background: 'linear-gradient(45deg, #F59E0B 30%, #EAB545 90%)',
                transform: 'scale(1.1)',
                boxShadow: '0 6px 16px rgba(234, 181, 69, 0.5)',
              },
            }}
          >
            <Add fontSize="medium" />
          </IconButton>
        ) : (
          <Box
            sx={{
              position: 'absolute',
              bottom: 12,
              right: 12,
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.85)',
              borderRadius: 2,
              padding: '6px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
            }}
          >
            <IconButton
              onClick={(e) => handleQuantityChange(e, currentQuantity - 1)}
              size="small"
              sx={{
                color: 'white',
                width: 32,
                height: 32,
                '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.15)' },
              }}
            >
              <Remove fontSize="small" />
            </IconButton>
            <Typography
              variant="body1"
              fontWeight="bold"
              color="white"
              sx={{ mx: 1.5, minWidth: 24, textAlign: 'center' }}
            >
              {currentQuantity}
            </Typography>
            <IconButton
              onClick={(e) => handleQuantityChange(e, currentQuantity + 1)}
              size="small"
              sx={{
                color: 'white',
                width: 32,
                height: 32,
                '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.15)' },
              }}
            >
              <Add fontSize="small" />
            </IconButton>
          </Box>
        )}
      </Box>
      
      {/* Контент - адаптивная высота */}
      <CardContent 
        sx={{ 
          height: { xs: 240, sm: 240 },
          display: 'flex', 
          flexDirection: 'column',
          p: { xs: 2.5, sm: 2 },
          '&:last-child': { pb: { xs: 2.5, sm: 2 } }
        }}
      >
        {/* Название - фиксированная высота */}
        <Box sx={{ height: { xs: 60, sm: 56 }, mb: 1 }}>
          <Typography 
            variant="h6" 
            component="h3" 
            sx={{ 
              fontWeight: 'bold',
              fontSize: { xs: '1.1rem', sm: '1rem' },
              lineHeight: 1.4,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              color: 'text.primary',
              height: '100%'
            }}
          >
            {product.name || 'Название товара'}
          </Typography>
        </Box>
        
        {/* Описание - адаптивная высота */}
        <Box sx={{ height: { xs: 90, sm: 84 }, mb: 2 }}>
          <Typography 
            variant="body2" 
            color="text.secondary"
            sx={{
              fontSize: { xs: '0.9rem', sm: '0.875rem' },
              lineHeight: 1.4,
              display: '-webkit-box',
              WebkitLineClamp: { xs: 4, sm: 4 },
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              height: '100%'
            }}
          >
            {(product.description && product.description.trim()) 
              ? product.description 
              : 'Вкусное блюдо от наших поваров. Приготовлено из качественных ингредиентов с любовью.'
            }
          </Typography>
        </Box>
        
        {/* Вес - фиксированная высота */}
        <Box sx={{ height: 32, display: 'flex', justifyContent: 'center', alignItems: 'center', mb: 1 }}>
          {product.weight > 0 ? (
            <Chip
              label={`${product.weight}г`}
              size="small"
              sx={{
                backgroundColor: 'rgba(58, 58, 55, 1)',
                color: 'text.secondary',
                border: '1px solid #6B7280',
                fontSize: '0.75rem',
                height: 26,
                borderRadius: 1.5,
              }}
            />
          ) : (
            <Box sx={{ height: 26 }} />
          )}
        </Box>
        
        {/* Цена - всегда внизу */}
        <Box 
          display="flex" 
          justifyContent="space-between" 
          alignItems="center"
          sx={{ mt: 'auto', height: 48 }}
        >
          <Typography 
            variant="h5" 
            component="span" 
            fontWeight="bold" 
            color="primary.main"
            sx={{ fontSize: { xs: '1.5rem', sm: '1.4rem' } }}
          >
            {product.isCustomizable ? `от ₽${product.price || 0}` : `₽${product.price || 0}`}
          </Typography>
          
          {/*/!* Дополнительные кнопки управления количеством внизу карточки *!/*/}
          {/*{currentQuantity > 0 && !product.isCustomizable && (*/}
          {/*  <ButtonGroup size="small" variant="outlined">*/}
          {/*    <IconButton*/}
          {/*      onClick={(e) => handleQuantityChange(e, currentQuantity - 1)}*/}
          {/*      sx={{*/}
          {/*        backgroundColor: 'rgba(58, 58, 55, 1)',*/}
          {/*        border: '1px solid #6B7280',*/}
          {/*        color: 'text.secondary',*/}
          {/*        width: 34,*/}
          {/*        height: 34,*/}
          {/*        '&:hover': { backgroundColor: 'rgba(107, 114, 128, 0.1)' },*/}
          {/*      }}*/}
          {/*    >*/}
          {/*      <Remove fontSize="small" />*/}
          {/*    </IconButton>*/}
          {/*    <Box*/}
          {/*      display="flex"*/}
          {/*      alignItems="center"*/}
          {/*      justifyContent="center"*/}
          {/*      sx={{*/}
          {/*        minWidth: 42,*/}
          {/*        backgroundColor: 'background.paper',*/}
          {/*        border: '1px solid #6B7280',*/}
          {/*        borderLeft: 'none',*/}
          {/*        borderRight: 'none',*/}
          {/*      }}*/}
          {/*    >*/}
          {/*      <Typography variant="body2" fontWeight="bold" color="text.primary">*/}
          {/*        {currentQuantity}*/}
          {/*      </Typography>*/}
          {/*    </Box>*/}
          {/*    <IconButton*/}
          {/*      onClick={(e) => handleQuantityChange(e, currentQuantity + 1)}*/}
          {/*      sx={{*/}
          {/*        backgroundColor: 'primary.main',*/}
          {/*        color: 'white',*/}
          {/*        width: 34,*/}
          {/*        height: 34,*/}
          {/*        '&:hover': { backgroundColor: 'secondary.main' },*/}
          {/*      }}*/}
          {/*    >*/}
          {/*      <Add fontSize="small" />*/}
          {/*    </IconButton>*/}
          {/*  </ButtonGroup>*/}
          {/*)}*/}
        </Box>
      </CardContent>
    </Card>
  );
};