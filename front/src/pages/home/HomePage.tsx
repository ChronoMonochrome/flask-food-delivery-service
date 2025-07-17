import React, { useEffect, useState } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  AppBar, 
  Toolbar, 
  IconButton,
  Grid,
  Paper
} from '@mui/material';
import { Phone } from '@mui/icons-material';
import { useGetCategoriesQuery, useGetProductsQuery } from '../../shared/api';
import { mapApiCategoryToCategory, mapApiProductToProduct } from '../../shared/utils/mappers';
import { CategorySlider } from '../../widgets/category-slider/CategorySlider';
import { ProductCard } from '../../widgets/product-card/ProductCard';
import { BottomNav } from '../../widgets/bottom-nav/BottomNav';
import { LoadingSpinner } from '../../shared/ui/LoadingSpinner';
import { ErrorMessage } from '../../shared/ui/ErrorMessage';

export const HomePage: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('');

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

  // Добавляем конструктор WOK для категории WOK
  if (selectedCategory === 'f7ec3fe3-4cea-4ee1-9b9b-cb98463355c7') {
    // Создаем товар-конструктор на основе данных с бэкенда
    const wokBuilderProduct = {
      id: 'wok-builder',
      name: 'Собери свою коробочку',
      description: 'Создай свой уникальный WOK! Выбери основу, добавь мясо и начинки по вкусу',
      price: 210, // Базовая цена, будет пересчитана в конструкторе
      image: 'https://images.pexels.com/photos/1640774/pexels-photo-1640774.jpeg?auto=compress&cs=tinysrgb&w=400',
      categoryId: selectedCategory,
      weight: 330,
      nutrition: { calories: 250, protein: 8, fat: 5, carbs: 45 },
      ingredients: ['основа', 'овощи', 'соус'],
      isCustomizable: true,
      recommendations: []
    };
    products = [wokBuilderProduct, ...products];
  }

  useEffect(() => {
    if (categories.length > 0 && !selectedCategory) {
      setSelectedCategory(categories[0].id);
    }
  }, [categories, selectedCategory]);

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
                  justifyContent: { xs: 'center', sm: 'flex-start' },
                  alignItems: 'stretch',
                }}
              >
                {products.map((product) => (
                  <Grid 
                    item 
                    xs={12}
                    sm={6}
                    md={6}
                    lg={4}
                    xl={3}
                    key={product.id}
                    sx={{ 
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'stretch',
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