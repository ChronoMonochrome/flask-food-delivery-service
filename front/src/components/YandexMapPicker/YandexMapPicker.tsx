import React, { useEffect, useRef, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  CircularProgress,
  Alert
} from '@mui/material';
import { useReverseGeocodeMutation } from '../../shared/api/geocoding-api';

interface YandexMapPickerProps {
  open: boolean;
  onClose: () => void;
  onAddressSelect: (address: string, coordinates: [number, number], deliveryCost: number) => void;
}

export const YandexMapPicker: React.FC<YandexMapPickerProps> = ({
  open,
  onClose,
  onAddressSelect
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const placemarkRef = useRef<any>(null);
  
  const [selectedCoordinates, setSelectedCoordinates] = useState<[number, number] | null>(null);
  const [isMapLoading, setIsMapLoading] = useState(true);
  const [mapError, setMapError] = useState<string | null>(null);
  
  const [reverseGeocode, { isLoading: isGeocoding }] = useReverseGeocodeMutation();

  // Загружаем скрипт Яндекс.Карт только один раз
  useEffect(() => {
    if (!(window as any).ymaps && !document.querySelector('script[src*="api-maps.yandex.ru"]')) {
      const script = document.createElement('script');
      script.src = 'https://api-maps.yandex.ru/2.1/?lang=ru_RU';
      script.async = true;
      document.head.appendChild(script);
    }
  }, []);

  // Инициализируем карту при открытии диалога
  useEffect(() => {
    if (!open) return;

    setIsMapLoading(true);
    setMapError(null);
    setSelectedCoordinates([56.0167, 38.3833]); // Координаты Черноголовки по умолчанию

    const initMap = () => {
      if (!mapRef.current) return;

      try {
        // Очищаем предыдущую карту если есть
        if (mapInstanceRef.current) {
          mapInstanceRef.current.destroy();
          mapInstanceRef.current = null;
          placemarkRef.current = null;
        }

        // Создаем новую карту
        const newMap = new (window as any).ymaps.Map(mapRef.current, {
          center: [56.0167, 38.3833],
          zoom: 13,
          controls: ['zoomControl', 'fullscreenControl']
        });

        // Создаем плейсмарк
        const newPlacemark = new (window as any).ymaps.Placemark([56.0167, 38.3833], {
          hintContent: 'Перетащите метку для выбора адреса',
          balloonContent: 'Выберите точку доставки'
        }, {
          preset: 'islands#redDotIcon',
          draggable: true
        });

        // Добавляем плейсмарк на карту
        newMap.geoObjects.add(newPlacemark);

        // Обработчик перетаскивания метки
        newPlacemark.events.add('dragend', () => {
          const coords = newPlacemark.geometry.getCoordinates();
          setSelectedCoordinates([coords[0], coords[1]]);
        });

        // Обработчик клика по карте
        newMap.events.add('click', (e: any) => {
          const coords = e.get('coords');
          newPlacemark.geometry.setCoordinates(coords);
          setSelectedCoordinates([coords[0], coords[1]]);
        });

        mapInstanceRef.current = newMap;
        placemarkRef.current = newPlacemark;
        setIsMapLoading(false);
      } catch (error) {
        console.error('Ошибка инициализации карты:', error);
        setMapError('Ошибка инициализации карты');
        setIsMapLoading(false);
      }
    };

    if ((window as any).ymaps) {
      (window as any).ymaps.ready(initMap);
    } else {
      // Ждем загрузки API
      const checkYmaps = setInterval(() => {
        if ((window as any).ymaps) {
          clearInterval(checkYmaps);
          (window as any).ymaps.ready(initMap);
        }
      }, 100);

      // Таймаут на случай если API не загрузится
      setTimeout(() => {
        clearInterval(checkYmaps);
        if (!(window as any).ymaps) {
          setMapError('Не удалось загрузить Яндекс.Карты');
          setIsMapLoading(false);
        }
      }, 10000);
    }
  }, [open]);

  // Очищаем карту при закрытии
  useEffect(() => {
    if (!open && mapInstanceRef.current) {
      mapInstanceRef.current.destroy();
      mapInstanceRef.current = null;
      placemarkRef.current = null;
    }
  }, [open]);

  const handleConfirmAddress = async () => {
    if (!selectedCoordinates) return;

    try {
      let address = `Координаты: ${selectedCoordinates[0].toFixed(6)}, ${selectedCoordinates[1].toFixed(6)}`;
      
      // Пробуем получить адрес через Яндекс.Карты API
      if ((window as any).ymaps) {
        try {
          // Получаем адрес и стоимость доставки с бэкенда
          const geocodeResult = await (window as any).ymaps.geocode(selectedCoordinates, {
            kind: 'house',
            results: 1
          });
          
          console.log('Результат геокодирования:', geocodeResult);
          
          const firstGeoObject = geocodeResult.geoObjects.get(0);
          console.log('Первый объект:', firstGeoObject);
          
          if (firstGeoObject) {
            const addressLine = firstGeoObject.getAddressLine();
            console.log('Полученный адрес:', addressLine);
            
            if (addressLine && addressLine.trim()) {
              address = addressLine;
            } else {
              // Пробуем получить адрес другим способом
              const thoroughfareName = firstGeoObject.getThoroughfare();
              const premiseNumber = firstGeoObject.getPremiseNumber();
              const localityName = firstGeoObject.getLocalities().join(', ');
              
              console.log('Альтернативные данные:', { thoroughfareName, premiseNumber, localityName });
              
              if (localityName) {
                address = localityName;
                if (thoroughfareName) address += `, ${thoroughfareName}`;
                if (premiseNumber) address += `, ${premiseNumber}`;
              }
            }
          }
        } catch (geocodeError) {
          console.error('Ошибка геокодирования Яндекс.Карт:', geocodeError);
          // Оставляем координаты как fallback
        }
      } else {
        console.warn('Яндекс.Карты API недоступен для геокодирования');
      }
      
      console.log('Финальный адрес:', address);
      
      const deliveryResult = await reverseGeocode({
        latitude: selectedCoordinates[0],
        longitude: selectedCoordinates[1]
      }).unwrap();
      
      const finalAddress = deliveryResult.address || `Координаты: ${selectedCoordinates[0].toFixed(6)}, ${selectedCoordinates[1].toFixed(6)}`;
      const deliveryCost = deliveryResult.delivery_cost;
      
      onAddressSelect(finalAddress, selectedCoordinates, deliveryCost);
      onClose();
    } catch (error) {
      console.error('Ошибка получения адреса и стоимости доставки:', error);
      const fallbackAddress = `Координаты: ${selectedCoordinates[0].toFixed(6)}, ${selectedCoordinates[1].toFixed(6)}`;
      onAddressSelect(fallbackAddress, selectedCoordinates, 0);
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          backgroundColor: 'background.paper',
          border: '1px solid #4B5563',
          borderRadius: 3,
        }
      }}
    >
      <DialogTitle sx={{ color: 'text.primary', fontWeight: 'bold' }}>
        Выберите адрес доставки
      </DialogTitle>
      
      <DialogContent>
        <Typography variant="body2" color="text.secondary" mb={2}>
          Кликните по карте или перетащите метку для выбора точки доставки
        </Typography>
        
        {mapError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {mapError}
          </Alert>
        )}
        
        <Box
          ref={mapRef}
          sx={{
            width: '100%',
            height: 400,
            borderRadius: 2,
            border: '1px solid #4B5563',
            position: 'relative',
            backgroundColor: '#f5f5f5'
          }}
        >
          {isMapLoading && (
            <Box
              display="flex"
              alignItems="center"
              justifyContent="center"
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.1)',
                zIndex: 1000
              }}
            >
              <Box textAlign="center">
                <CircularProgress sx={{ color: 'primary.main', mb: 2 }} />
                <Typography variant="body2" color="text.secondary">
                  Загрузка карты...
                </Typography>
              </Box>
            </Box>
          )}
        </Box>
        
        {selectedCoordinates && (
          <Typography variant="caption" color="text.secondary" mt={1} display="block">
            Координаты: {selectedCoordinates[0].toFixed(6)}, {selectedCoordinates[1].toFixed(6)}
          </Typography>
        )}
      </DialogContent>
      
      <DialogActions sx={{ p: 3, pt: 1 }}>
        <Button
          onClick={onClose}
          variant="outlined"
          sx={{ borderColor: '#6B7280', color: 'text.primary' }}
        >
          Отмена
        </Button>
        <Button
          onClick={handleConfirmAddress}
          variant="contained"
          disabled={!selectedCoordinates || isGeocoding || isMapLoading}
          sx={{ ml: 2 }}
        >
          {isGeocoding ? (
            <>
              <CircularProgress size={16} sx={{ mr: 1 }} />
              Определяем адрес...
            </>
          ) : (
            'Подтвердить адрес'
          )}
        </Button>
      </DialogActions>
    </Dialog>
  );
};