import React, {useEffect} from 'react';
import { useDispatch } from 'react-redux';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  AppBar,
  Toolbar,
  IconButton,
  Chip,
  Stack
} from '@mui/material';
import { 
  ArrowBack, 
  Schedule, 
  CheckCircle, 
  LocalShipping, 
  Cancel,
  Inventory,
  Assignment
} from '@mui/icons-material';
import { navigationActions } from '../../features/navigation';
import { BottomNav } from '../../widgets/bottom-nav/BottomNav';
import {useGetOrdersQuery} from "../../shared/api/orderApi.ts";


// Mock data для заказов
const mockOrders = [
  {
    id: '1',
    items: [
      {
        product: { name: 'Маргарита', price: 590 },
        quantity: 1,
        selectedAddons: [{ name: 'Кетчуп', price: 15 }],
        selectedRecommendations: [{ name: 'Кола 0.5л', price: 120 }]
      }
    ],
    total: 725,
    deliveryInfo: {
      address: 'ул. Пушкина, д. 10, кв. 5',
      phone: '+7 (999) 123-45-67',
      paymentMethod: 'cash',
      comment: 'Домофон не работает'
    },
    status: 'delivering',
    createdAt: new Date(Date.now() - 30 * 60 * 1000),
    estimatedDelivery: new Date(Date.now() + 15 * 60 * 1000)
  },
  {
    id: '2',
    items: [
      {
        product: { name: 'Классический бургер', price: 450 },
        quantity: 2,
        selectedAddons: [],
        selectedRecommendations: [{ name: 'Картофель фри', price: 180 }]
      }
    ],
    total: 1080,
    deliveryInfo: {
      address: 'пр. Ленина, д. 25',
      phone: '+7 (999) 987-65-43',
      paymentMethod: 'card',
      comment: ''
    },
    status: 'delivered',
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000)
  }
];

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'pending':
      return <Schedule sx={{ color: 'warning.main' }} />;
    case 'preparing':
      return <Inventory sx={{ color: 'info.main' }} />;
    case 'delivering':
      return <LocalShipping sx={{ color: 'primary.main' }} />;
    case 'delivered':
      return <CheckCircle sx={{ color: 'success.main' }} />;
    case 'cancelled':
      return <Cancel sx={{ color: 'error.main' }} />;
    default:
      return <Schedule sx={{ color: 'text.disabled' }} />;
  }
};

const getStatusText = (status: string) => {
  switch (status) {
    case 'pending':
      return 'Ожидает подтверждения';
    case 'preparing':
      return 'Готовится';
    case 'delivering':
      return 'В пути';
    case 'delivered':
      return 'Доставлен';
    case 'cancelled':
      return 'Отменен';
    default:
      return 'Неизвестно';
  }
};

const formatDate = (date: string | Date) => {
  const d = date instanceof Date ? date : new Date(date)
  return d.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export const MyOrdersPage: React.FC = () => {
  const dispatch = useDispatch();

  const { data, error, isLoading } = useGetOrdersQuery(undefined, {
    refetchOnMountOrArgChange: true,
  })

  console.log(12331231231,data)

  const handleBack = () => {
    dispatch(navigationActions.navigateToPage('home'));
  };


  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default', pb: 10 }}>
      <AppBar position="static" sx={{ backgroundColor: 'background.paper', boxShadow: 'none' }}>
        <Toolbar sx={{ borderBottom: '1px solid #4B5563' }}>
          <IconButton onClick={handleBack} sx={{ mr: 2 }}>
            <ArrowBack sx={{ color: 'text.secondary' }} />
          </IconButton>
          <Typography variant="h6" fontWeight="bold" color="text.primary">
            Мои заказы
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 3 }}>
        <Stack spacing={2}>
          {data?.map((order) => (
            <Card key={order?.id} sx={{ backgroundColor: 'background.paper', border: '1px solid #4B5563' }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Box display="flex" alignItems="center" gap={1}>
                    {getStatusIcon(order?.status)}
                    <Typography variant="h6" fontWeight="bold" color="text.primary">
                      Заказ #{order?.id}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {formatDate(order?.createdAt)}
                  </Typography>
                </Box>

                <Box mb={3}>
                {/*  <Box display="flex" justifyContent="space-between" mb={1}>*/}
                {/*    <Typography variant="body2" color="text.secondary">Статус:</Typography>*/}
                {/*    <Typography variant="body2" fontWeight="medium" color="text.primary">*/}
                {/*      {getStatusText(order.status)}*/}
                {/*    </Typography>*/}
                {/*  </Box>*/}

                  {/*{order.estimatedDelivery && order.status === 'delivering' && (*/}
                  {/*  <Box display="flex" justifyContent="space-between" mb={1}>*/}
                  {/*    <Typography variant="body2" color="text.secondary">Ожидаемое время:</Typography>*/}
                  {/*    <Typography variant="body2" fontWeight="medium" color="primary.main">*/}
                  {/*      {formatDate(order.estimatedDelivery)}*/}
                  {/*    </Typography>*/}
                  {/*  </Box>*/}
                  {/*)}*/}

                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">Адрес:</Typography>
                    <Typography variant="body2" fontWeight="medium" color="text.primary" sx={{ textAlign: 'right', flex: 1, ml: 1 }}>
                      {[
                        order?.deliveryInfo?.city_name && `г. ${order.deliveryInfo.city_name}`,
                        order?.deliveryInfo?.street_name && `ул. ${order.deliveryInfo.street_name}`,
                        order?.deliveryInfo?.house_number && `д. ${order.deliveryInfo.house_number}`,
                        order?.deliveryInfo?.apartment && `кв. ${order.deliveryInfo.apartment}`
                      ]
                          .filter(Boolean) // убираем пустые
                          .join(', ')}
                      {/*{ order?.deliveryInfo?.address}*/}
                    </Typography>
                  </Box>
                </Box>

                <Box sx={{ borderTop: '1px solid #4B5563', pt: 2 }}>
                  <Typography variant="h6" fontWeight="bold" color="text.primary" mb={2}>
                    Состав заказа:
                  </Typography>
                  <Stack spacing={1}>
                    {order?.items?.map((item, index) => (
                      <Box key={index}>
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="body2" color="text.secondary">
                            {item?.product?.name} × {item.quantity}
                          </Typography>
                          <Typography variant="body2" fontWeight="medium" color="text.primary">
                            {(
                                item?.product?.price +
                                item?.selectedAddons?.reduce(
                                    (sum, addon) => sum + (addon?.addon?.price || 0) * (addon?.quantity || 0),
                                    0
                                )
                            ).toLocaleString('ru-RU')} ₽
                          </Typography>
                        </Box>
                        {item?.selectedAddons?.length > 0 && (
                        <Box sx={{ ml: 1 }}>
                          {item?.selectedAddons?.map((addon, i) => (
                              <Typography
                                  key={i}
                                  variant="caption"
                                  color="primary.main"
                                  display="block"
                              >
                                + {addon.addon.name} × {addon.quantity}
                              </Typography>
                          ))}
                        </Box>
                        )}
                      </Box>
                    ))}
                  </Stack>

                  <Box sx={{ borderTop: '1px solid #4B5563', pt: 1, mt: 2 }}>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="h6" fontWeight="bold" color="text.primary">Итого:</Typography>
                      <Typography variant="h6" fontWeight="bold" color="primary.main">₽{order?.total?.toLocaleString()}</Typography>
                    </Box>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
          
          {mockOrders.length === 0 && (
            <Box textAlign="center" py={8}>
              <Assignment sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h5" fontWeight="bold" color="text.primary" mb={1}>
                Заказов пока нет
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Сделайте свой первый заказ!
              </Typography>
            </Box>
          )}
        </Stack>
      </Container>

      <BottomNav />
    </Box>
  );
};