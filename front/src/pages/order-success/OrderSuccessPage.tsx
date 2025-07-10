import React from 'react';
import { useDispatch } from 'react-redux';
import {
  Box,
  Container,
  Typography,
  Button,
  Card,
  CardContent
} from '@mui/material';
import { CheckCircle, Home } from '@mui/icons-material';
import { navigationActions } from '../../features/navigation';

export const OrderSuccessPage: React.FC = () => {
  const dispatch = useDispatch();

  const handleBackToHome = () => {
    dispatch(navigationActions.navigateToPage('home'));
  };

  return (
    <Box 
      sx={{ 
        minHeight: '100vh', 
        background: 'linear-gradient(45deg, #EAB545 30%, #F59E0B 90%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        px: 3
      }}
    >
      <Card 
        sx={{ 
          backgroundColor: 'background.paper',
          borderRadius: 6,
          maxWidth: 400,
          width: '100%',
          border: '1px solid #4B5563',
          boxShadow: 6
        }}
      >
        <CardContent sx={{ textAlign: 'center', p: 4 }}>
          <CheckCircle sx={{ fontSize: 80, color: 'success.main', mb: 3 }} />
          <Typography variant="h4" component="h1" fontWeight="bold" color="text.primary" mb={2}>
            Заказ принят!
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={4}>
            Мы получили ваш заказ и уже готовим его. Ожидайте звонка курьера.
          </Typography>
          
          <Card sx={{ backgroundColor: '#374151', mb: 4, border: '1px solid #4B5563' }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" color="text.primary" mb={1}>
                Время доставки
              </Typography>
              <Typography variant="h5" fontWeight="bold" color="primary.main">
                45-60 минут
              </Typography>
            </CardContent>
          </Card>

          <Button
            onClick={handleBackToHome}
            variant="contained"
            size="large"
            startIcon={<Home />}
            sx={{
              width: '100%',
              py: 2,
              borderRadius: 2,
              fontSize: '1.125rem',
              fontWeight: 'bold',
            }}
          >
            На главную
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
};