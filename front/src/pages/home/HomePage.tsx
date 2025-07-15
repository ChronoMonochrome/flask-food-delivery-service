import React, { useEffect, useState } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  AppBar, 
  Toolbar, 
  IconButton,
  Grid,
} from '@mui/material';
import { Phone } from '@mui/icons-material';
import { useGetCategoriesQuery, useGetProductsQuery } from '../../shared/api';
import { mapApiCategoryToCategory, mapApiProductToProduct } from '../../shared/utils/mappers';
import { wokBuilderProduct } from '../../shared/constants/wok-data';
import { CategorySlider } from '../../widgets/category-slider/CategorySlider';
import { ProductCard } from '../../widgets/product-card/ProductCard';
import { BottomNav } from '../../widgets/bottom-nav/BottomNav';
import { LoadingSpinner } from '../../shared/ui/LoadingSpinner';
import { ErrorMessage } from '../../shared/ui/ErrorMessage';

export const HomePage: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [userTg, setUserTg] = useState(null);
  const [debug, setDebug] = useState("");

  const { 
    data: apiCategories, 
    isLoading: categoriesLoading, 
    error: categoriesError 
  } = useGetCategoriesQuery();

  const { 
    data: apiProducts, 
    isLoading: productsLoading, 
    error: productsError 
  } = useGetProductsQuery(
    { categoryId: selectedCategory },
    { skip: !selectedCategory }
  );

  const categories = apiCategories ? apiCategories.map(mapApiCategoryToCategory) : [];
  let products = apiProducts ? apiProducts.map(mapApiProductToProduct) : [];

  // Добавляем конструктор WOK для категории '9'
  if (selectedCategory === '9') {
    products = [wokBuilderProduct, ...products];
  }

  useEffect(() => {
    if (categories.length > 0 && !selectedCategory) {
      setSelectedCategory(categories[0].id);
    }
  }, [categories, selectedCategory]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      const tg = window?.Telegram?.WebApp

      if (!tg) {
        setDebug('❗ Telegram WebApp API не найден. Возможно, вы открыли сайт вне Telegram.')
        return
      }

      tg.ready()

      if (tg.initDataUnsafe?.user) {
        setUserTg(tg.initDataUnsafe.user)
      } else {
        setDebug('⚠️ Пользователь не передан в initDataUnsafe.')
      }
    }, 300) // 100–300 мс обычно хватает

    return () => clearTimeout(timeout)
  }, [])

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default', pb: 10 }}>
      {/* Header */}
      <AppBar position="static" sx={{ backgroundColor: 'background.default', boxShadow: 'none' }}>
        <Toolbar sx={{ borderBottom: '1px solid #4B5563' }}>
          <Box display="flex" alignItems="center" flexGrow={1}>
            <Box component="img" src="/logo_orange.png" alt="Мандарин" sx={{ width: 64, height: 64, mr: 2 }} />
            <Box>
              <Typography variant="h6" component="h1" fontWeight="bold" color="text.primary">
                Мандарин
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.4 }}>
                Доставка ежедневно по Черноголовке и ближайшим населенным пунктам
              </Typography>
            </Box>
          </Box>
          <IconButton 
            sx={{ 
              backgroundColor: 'background.paper',
              border: '1px solid #4B5563',
              '&:hover': { backgroundColor: 'rgba(107, 114, 128, 0.1)' }
            }}
          >
            <Phone sx={{ color: 'primary.main' }} />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Category Slider */}
      {categoriesLoading ? (
        <LoadingSpinner />
      ) : categoriesError ? (
        <ErrorMessage message="Ошибка загрузки категорий" />
      ) : (
        <CategorySlider
          categories={categories}
          selectedCategory={selectedCategory}
          onCategorySelect={setSelectedCategory}
        />
      )}

      {/* Products Grid */}
      <Container maxWidth="xl" sx={{ px: 2 }}>
        {selectedCategory && (
          <>
            <Typography variant="h5" component="h2" fontWeight="bold" color="text.primary" mb={3}>
              {debug}
              {userTg ? userTg : "gg"}
              {categories.find(c => c.id === selectedCategory)?.name}
            </Typography>
            
            {productsLoading ? (
              <LoadingSpinner />
            ) : productsError ? (
              <ErrorMessage message="Ошибка загрузки товаров" />
            ) : (
              <Grid 
                container 
                spacing={3} 
                sx={{ 
                  justifyContent: 'flex-start',
                  alignItems: 'stretch'
                }}
              >
                {products.map((product) => (
                  <Grid 
                    item 
                    xs={12} 
                    sm={6} 
                    md={6} 
                    lg={4} 
                    xl={4} 
                    key={product.id}
                    sx={{ 
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'stretch'
                    }}
                  >
                    <ProductCard product={product} />
                  </Grid>
                ))}
              </Grid>
            )}
          </>
        )}
      </Container>

      <BottomNav />
    </Box>
  );
};