import React, { useState } from 'react';
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
  Stepper,
  Step,
  StepLabel,
  AppBar,
  Toolbar,
  Stack,
} from '@mui/material';
import { ArrowBack, Check } from '@mui/icons-material';
import { useNavigationSelector } from '../../features/navigation';
import { useCartOperations } from '../../entities/cart';
import { navigationActions } from '../../features/navigation';
import { WokCustomization } from '../../shared/types';
import { useGetWokAddonsByGroupQuery, WokAddon } from '../../shared/api';
import { LoadingSpinner } from '../../shared/ui/LoadingSpinner';
import { ErrorMessage } from '../../shared/ui/ErrorMessage';

type Step = 'base' | 'meat' | 'toppings' | 'sauces' | 'summary';

const steps = ['Основа', 'Мясо', 'Начинки', 'Соусы', 'Готово'];

export const WokBuilderPage: React.FC = () => {
  const dispatch = useDispatch();
  const { selectedProduct } = useNavigationSelector();
  const { addToCart } = useCartOperations();
  const [currentStep, setCurrentStep] = useState<Step>('base');
  const [selectedBase, setSelectedBase] = useState<WokAddon | null>(null);
  const [selectedMeats, setSelectedMeats] = useState<WokAddon[]>([]);
  const [selectedToppings, setSelectedToppings] = useState<WokAddon[]>([]);
  const [selectedSauces, setSelectedSauces] = useState<WokAddon[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Загружаем данные с бэкенда
  const { data: bases, isLoading: basesLoading, error: basesError } = useGetWokAddonsByGroupQuery('Лапша');
  const { data: meats, isLoading: meatsLoading, error: meatsError } = useGetWokAddonsByGroupQuery('Мясо');
  const { data: toppings, isLoading: toppingsLoading, error: toppingsError } = useGetWokAddonsByGroupQuery('Начинка');
  const { data: sauces, isLoading: saucesLoading, error: saucesError } = useGetWokAddonsByGroupQuery('Соусы');

  if (!selectedProduct) {
    return null;
  }

  const handleMeatToggle = (meat: WokAddon) => {
    setSelectedMeats(prev => 
      prev.find(m => m.id === meat.id)
        ? prev.filter(m => m.id !== meat.id)
        : [...prev, meat]
    );
  };

  const handleToppingToggle = (topping: WokAddon) => {
    setSelectedToppings(prev => 
      prev.find(t => t.id === topping.id)
        ? prev.filter(t => t.id !== topping.id)
        : [...prev, topping]
    );
  };

  const handleSauceToggle = (sauce: WokAddon) => {
    setSelectedSauces(prev => 
      prev.find(s => s.id === sauce.id)
        ? prev.filter(s => s.id !== sauce.id)
        : [...prev, sauce]
    );
  };

  const getTotalPrice = () => {
    const basePrice = selectedBase?.price || 0;
    const meatsPrice = selectedMeats.reduce((sum, meat) => sum + meat.price, 0);
    const toppingsPrice = selectedToppings.reduce((sum, topping) => sum + topping.price, 0);
    const saucesPrice = selectedSauces.reduce((sum, sauce) => sum + sauce.price, 0);
    return basePrice + meatsPrice + toppingsPrice + saucesPrice;
  };

  const handleAddToCart = async () => {
    if (!selectedBase) return;
    
    setIsLoading(true);
    try {
      const customWok: WokCustomization = {
        base: {
          id: selectedBase.id,
          name: selectedBase.name,
          price: selectedBase.price,
          image: selectedBase.image || 'https://images.pexels.com/photos/723198/pexels-photo-723198.jpeg?auto=compress&cs=tinysrgb&w=200'
        },
        meats: selectedMeats.map(meat => ({
          id: meat.id,
          name: meat.name,
          price: meat.price,
          image: meat.image || 'https://images.pexels.com/photos/616354/pexels-photo-616354.jpeg?auto=compress&cs=tinysrgb&w=200'
        })),
        toppings: selectedToppings.map(topping => ({
          id: topping.id,
          name: topping.name,
          price: topping.price,
          image: topping.image || 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200'
        })),
        sauces: selectedSauces.map(sauce => ({
          id: sauce.id,
          name: sauce.name,
          price: sauce.price,
          image: sauce.image || 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200'
        }))
      };

      const customProduct = {
        ...selectedProduct,
        name: `Собери свою коробочку`,
        description: `${selectedBase.name} с ${[...selectedMeats, ...selectedToppings, ...selectedSauces].map(item => item.name.toLowerCase()).join(', ')}`,
        price: getTotalPrice(),
        recommendations: selectedProduct.recommendations || []
      };

      await addToCart(customProduct, [], [], customWok);
      dispatch(navigationActions.navigateToPage('home'));
    } catch (error) {
      console.error('Ошибка добавления WOK в корзину:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    dispatch(navigationActions.navigateToPage('home'));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 'base':
        return selectedBase !== null;
      case 'meat':
      case 'toppings':
      case 'sauces':
        return true;
      case 'summary':
        return selectedBase !== null;
      default:
        return false;
    }
  };

  const getStepTitle = () => {
    switch (currentStep) {
      case 'base':
        return 'Шаг 1. Выбери основу';
      case 'meat':
        return 'Шаг 2. Добавь мясо';
      case 'toppings':
        return 'Шаг 3. Добавь начинку';
      case 'sauces':
        return 'Шаг 4. Добавь соус';
      case 'summary':
        return 'Твой WOK готов!';
      default:
        return '';
    }
  };

  const getActiveStep = () => {
    switch (currentStep) {
      case 'base': return 0;
      case 'meat': return 1;
      case 'toppings': return 2;
      case 'sauces': return 3;
      case 'summary': return 4;
      default: return 0;
    }
  };

  const getNextStep = (): Step => {
    switch (currentStep) {
      case 'base': return 'meat';
      case 'meat': return 'toppings';
      case 'toppings': return 'sauces';
      case 'sauces': return 'summary';
      default: return 'summary';
    }
  };

  const getPrevStep = (): Step => {
    switch (currentStep) {
      case 'meat': return 'base';
      case 'toppings': return 'meat';
      case 'sauces': return 'toppings';
      case 'summary': return 'sauces';
      default: return 'base';
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 'base':
        if (basesLoading) return <LoadingSpinner />;
        if (basesError) return <ErrorMessage message="Ошибка загрузки основ" />;
        if (!bases || bases.length === 0) return <ErrorMessage message="Основы не найдены" />;
        
        return (
          <Box>
            <Typography variant="body1" color="text.secondary" mb={3}>
              Выбери основу для своего WOK
            </Typography>
            <Grid container spacing={2}>
              {bases.map((base) => (
                <Grid item xs={6} key={base.id}>
                  <Card
                    onClick={() => setSelectedBase(base)}
                    sx={{
                      cursor: 'pointer',
                      backgroundColor: selectedBase?.id === base.id ? 'primary.main' : 'rgba(58, 58, 55, 1)',
                      border: selectedBase?.id === base.id ? 'none' : '1px solid #6B7280',
                      color: selectedBase?.id === base.id ? 'white' : 'text.primary',
                      '&:hover': {
                        backgroundColor: selectedBase?.id === base.id ? 'primary.dark' : 'rgba(107, 114, 128, 0.1)',
                      },
                    }}
                  >
                    <CardContent sx={{ textAlign: 'center', p: 2 }}>
                      <Box
                        component="img"
                        src={base.image || '/img.png'}
                        alt={base.name}
                        sx={{ width: '100%', height: 80, objectFit: 'cover', borderRadius: 2, mb: 1 }}
                      />
                      <Typography variant="body1" fontWeight="medium">{base.name}</Typography>
                      <Typography variant="h6" fontWeight="bold" color="primary.main">₽{base.price}</Typography>
                      {selectedBase?.id === base.id && (
                        <Check sx={{ mt: 1 }} />
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        );

      case 'meat':
        if (meatsLoading) return <LoadingSpinner />;
        if (meatsError) return <ErrorMessage message="Ошибка загрузки мяса" />;
        if (!meats || meats.length === 0) return <ErrorMessage message="Мясо не найдено" />;
        
        return (
          <Box>
            <Typography variant="body1" color="text.secondary" mb={3}>
              Выбери мясо по своему вкусу (можно несколько видов)
            </Typography>
            <Stack sx={{marginBottom:"120px"}} spacing={2}>
              {meats.map((meat) => (
                <Button
                  key={meat.id}
                  onClick={() => handleMeatToggle(meat)}
                  variant={selectedMeats.find(m => m.id === meat.id) ? 'contained' : 'outlined'}
                  sx={{
                    p: 2,
                    borderRadius: 3,
                    border: selectedMeats.find(m => m.id === meat.id) ? 'none' : '1px solid #6B7280',
                    backgroundColor: selectedMeats.find(m => m.id === meat.id) 
                      ? 'primary.main' 
                      : 'rgba(58, 58, 55, 1)',
                    '&:hover': {
                      backgroundColor: selectedMeats.find(m => m.id === meat.id) 
                        ? 'primary.dark' 
                        : 'rgba(107, 114, 128, 0.1)',
                    },
                  }}
                >
                  <Box display="flex" alignItems="center" width="100%">
                    <Box
                      component="img"
                      src={meat.image || '/img.png'}
                      alt={meat.name}
                      sx={{ width: 48, height: 48, borderRadius: 2, mr: 2, objectFit: 'cover' }}
                    />
                    <Box flexGrow={1} textAlign="left">
                      <Typography fontWeight="medium">{meat.name}</Typography>
                      <Typography variant="body2" sx={{ opacity: 0.75 }}>+₽{meat.price}</Typography>
                    </Box>
                    {selectedMeats.find(m => m.id === meat.id) && <Check />}
                  </Box>
                </Button>
              ))}
            </Stack>
          </Box>
        );

      case 'toppings':
        if (toppingsLoading) return <LoadingSpinner />;
        if (toppingsError) return <ErrorMessage message="Ошибка загрузки начинок" />;
        if (!toppings || toppings.length === 0) return <ErrorMessage message="Начинки не найдены" />;
        
        return (
          <Box>
            <Typography variant="body1" color="text.secondary" mb={3}>
              Добавь начинку по вкусу
            </Typography>
            <Stack sx={{marginBottom:"120px"}} spacing={2}>
              {toppings.map((topping) => (
                <Button
                  key={topping.id}
                  onClick={() => handleToppingToggle(topping)}
                  variant={selectedToppings.find(t => t.id === topping.id) ? 'contained' : 'outlined'}
                  sx={{
                    p: 2,
                    borderRadius: 3,
                    border: selectedToppings.find(t => t.id === topping.id) ? 'none' : '1px solid #6B7280',
                    backgroundColor: selectedToppings.find(t => t.id === topping.id) 
                      ? 'primary.main' 
                      : 'rgba(58, 58, 55, 1)',
                    '&:hover': {
                      backgroundColor: selectedToppings.find(t => t.id === topping.id) 
                        ? 'primary.dark' 
                        : 'rgba(107, 114, 128, 0.1)',
                    },
                  }}
                >
                  <Box display="flex" alignItems="center" width="100%">
                    <Box
                      component="img"
                      src={topping.image || '/img.png'}
                      alt={topping.name}
                      sx={{ width: 48, height: 48, borderRadius: 2, mr: 2, objectFit: 'cover' }}
                    />
                    <Box flexGrow={1} textAlign="left">
                      <Typography fontWeight="medium">{topping.name}</Typography>
                      <Typography variant="body2" sx={{ opacity: 0.75 }}>+₽{topping.price}</Typography>
                    </Box>
                    {selectedToppings.find(t => t.id === topping.id) && <Check />}
                  </Box>
                </Button>
              ))}
            </Stack>
          </Box>
        );

      case 'sauces':
        if (saucesLoading) return <LoadingSpinner />;
        if (saucesError) return <ErrorMessage message="Ошибка загрузки соусов" />;
        if (!sauces || sauces.length === 0) return <ErrorMessage message="Соусы не найдены" />;
        
        return (
          <Box>
            <Typography variant="body1" color="text.secondary" mb={3}>
              Выбери дополнительный соус
            </Typography>
            <Stack sx={{marginBottom:"120px"}} spacing={2}>
              {sauces.map((sauce) => (
                <Button
                  key={sauce.id}
                  onClick={() => handleSauceToggle(sauce)}
                  variant={selectedSauces.find(s => s.id === sauce.id) ? 'contained' : 'outlined'}
                  sx={{
                    p: 2,
                    borderRadius: 3,
                    border: selectedSauces.find(s => s.id === sauce.id) ? 'none' : '1px solid #6B7280',
                    backgroundColor: selectedSauces.find(s => s.id === sauce.id) 
                      ? 'primary.main' 
                      : 'rgba(58, 58, 55, 1)',
                    '&:hover': {
                      backgroundColor: selectedSauces.find(s => s.id === sauce.id) 
                        ? 'primary.dark' 
                        : 'rgba(107, 114, 128, 0.1)',
                    },
                  }}
                >
                  <Box display="flex" alignItems="center" width="100%">
                    <Box
                      component="img"
                      src={sauce.image || '/img.png'}
                      alt={sauce.name}
                      sx={{ width: 48, height: 48, borderRadius: 2, mr: 2, objectFit: 'cover' }}
                    />
                    <Box flexGrow={1} textAlign="left">
                      <Typography fontWeight="medium">{sauce.name}</Typography>
                      <Typography variant="body2" sx={{ opacity: 0.75 }}>+₽{sauce.price}</Typography>
                    </Box>
                    {selectedSauces.find(s => s.id === sauce.id) && <Check />}
                  </Box>
                </Button>
              ))}
            </Stack>
          </Box>
        );

      case 'summary':
        return (
          <Card sx={{ backgroundColor: 'rgba(58, 58, 55, 1)', border: '1px solid #6B7280' }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" color="text.primary" mb={2}>
                Состав твоего WOK:
              </Typography>
              
              {selectedBase && (
                <Box mb={1}>
                  <Typography component="span" color="primary.main" fontWeight="medium">Основа: </Typography>
                  <Typography component="span" color="text.secondary">{selectedBase.name} (₽{selectedBase.price})</Typography>
                </Box>
              )}
              
              {selectedMeats.length > 0 && (
                <Box mb={1}>
                  <Typography component="span" color="primary.main" fontWeight="medium">Мясо: </Typography>
                  <Typography component="span" color="text.secondary">
                    {selectedMeats.map(m => `${m.name} (+₽${m.price})`).join(', ')}
                  </Typography>
                </Box>
              )}
              
              {selectedToppings.length > 0 && (
                <Box mb={1}>
                  <Typography component="span" color="primary.main" fontWeight="medium">Начинки: </Typography>
                  <Typography component="span" color="text.secondary">
                    {selectedToppings.map(t => `${t.name} (+₽${t.price})`).join(', ')}
                  </Typography>
                </Box>
              )}
              
              {selectedSauces.length > 0 && (
                <Box mb={1}>
                  <Typography component="span" color="primary.main" fontWeight="medium">Соусы: </Typography>
                  <Typography component="span" color="text.secondary">
                    {selectedSauces.map(s => `${s.name} (+₽${s.price})`).join(', ')}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        );

      default:
        return null;
    }
  };

  // Показываем загрузку если загружается хотя бы одна группа
  const isAnyLoading = basesLoading || meatsLoading || toppingsLoading || saucesLoading;
  
  if (isAnyLoading) {
    return (
      <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default', display: 'flex', flexDirection: 'column' }}>
        <AppBar position="static" sx={{ backgroundColor: 'background.paper', boxShadow: 'none' }}>
          <Toolbar sx={{ borderBottom: '1px solid #4B5563' }}>
            <IconButton onClick={handleBack} sx={{ mr: 2 }}>
              <ArrowBack sx={{ color: 'text.secondary' }} />
            </IconButton>
            <Typography variant="h6" fontWeight="bold" color="text.primary">
              Собери свою коробочку
            </Typography>
          </Toolbar>
        </AppBar>
        <LoadingSpinner />
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
      {/* Header */}
      <AppBar position="static" sx={{ backgroundColor: 'background.paper', boxShadow: 'none' }}>
        <Toolbar sx={{ borderBottom: '1px solid #4B5563' }}>
          <IconButton onClick={handleBack} sx={{ mr: 2 }}>
            <ArrowBack sx={{ color: 'text.secondary' }} />
          </IconButton>
          <Box>
            <Typography variant="h6" fontWeight="bold" color="text.primary">
              Собери свою коробочку
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {getStepTitle()}
            </Typography>
          </Box>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 3 }}>
        {/* Progress */}
        <Stepper activeStep={getActiveStep()} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel sx={{ '& .MuiStepLabel-label': { color: 'text.secondary' } }}>
                {label}
              </StepLabel>
            </Step>
          ))}
        </Stepper>

        {renderStepContent()}
      </Container>

      {/* Bottom Actions */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 0,
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
          <Typography variant="h4" fontWeight="bold" color="primary.main">₽{getTotalPrice()}</Typography>
        </Box>
        
        <Stack direction="row" spacing={2}>
          {currentStep !== 'base' && (
            <Button
              onClick={() => setCurrentStep(getPrevStep())}
              variant="outlined"
              sx={{ flex: 1, py: 1.5, borderColor: '#6B7280', color: 'text.primary' }}
            >
              Назад
            </Button>
          )}
          
          {currentStep === 'summary' ? (
            <Button
              onClick={handleAddToCart}
              disabled={!canProceed() || isLoading}
              variant="contained"
              sx={{ flex: 1, py: 1.5, fontSize: '1rem', fontWeight: 'bold' }}
            >
              {isLoading ? 'Добавляем...' : 'Готово, в корзину!'}
            </Button>
          ) : (
            <Button
              onClick={() => setCurrentStep(getNextStep())}
              disabled={!canProceed()}
              variant="contained"
              sx={{ flex: 1, py: 1.5, fontSize: '1rem', fontWeight: 'bold' }}
            >
              {currentStep === 'base' ? 'Выбрать мясо' : 'Далее'}
            </Button>
          )}
        </Stack>
      </Box>
    </Box>
  );
};