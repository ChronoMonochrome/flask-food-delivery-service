import React, { useState, useCallback, useRef, useEffect } from 'react';
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
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {useLazyGetDeliveryCostQuery } from '../../shared/api/geocoding-api';

// Исправляем иконки маркеров Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface LeafletMapPickerProps {
  open: boolean;
  onClose: () => void;
  onAddressSelect: (address: string, coordinates: [number, number], deliveryCost: number) => void;
}

// Компонент для обработки кликов по карте
const MapClickHandler: React.FC<{
  onLocationSelect: (lat: number, lng: number) => void;
}> = ({ onLocationSelect }) => {
  useMapEvents({
    click: (e) => {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

// Компонент для перетаскиваемого маркера
const DraggableMarker: React.FC<{
  position: [number, number];
  onPositionChange: (lat: number, lng: number) => void;
}> = ({ position, onPositionChange }) => {
  const markerRef = useRef<L.Marker>(null);

  const eventHandlers = {
    dragend: () => {
      const marker = markerRef.current;
      if (marker != null) {
        const newPos = marker.getLatLng();
        onPositionChange(newPos.lat, newPos.lng);
      }
    },
  };

  return (
    <Marker
      draggable={true}
      eventHandlers={eventHandlers}
      position={position}
      ref={markerRef}
    />
  );
};

export const LeafletMapPicker: React.FC<LeafletMapPickerProps> = ({
  open,
  onClose,
  onAddressSelect
}) => {
  // Координаты Черноголовки по умолчанию
  const [selectedCoordinates, setSelectedCoordinates] = useState<[number, number]>([56.0167, 38.3833]);
  const [address, setAddress] = useState<string>('');
  const [isGeocodingAddress, setIsGeocodingAddress] = useState(false);
  const [addressError, setAddressError] = useState<string | null>(null);

  const [triggerGetDeliveryCost, { isFetching: isGettingDeliveryCost }] = useLazyGetDeliveryCostQuery();

  // Функция для получения адреса через Nominatim (OpenStreetMap)
  const getAddressFromCoordinates = useCallback(async (lat: number, lng: number) => {
    setIsGeocodingAddress(true);
    setAddressError(null);
    
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&accept-language=ru`
      );
      
      if (!response.ok) {
        throw new Error('Ошибка получения адреса');
      }
      
      const data = await response.json();
      
      if (data && data.display_name) {
        setAddress(data.display_name);
      } else {
        setAddress(`Координаты: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
      }
    } catch (error) {
      console.error('Ошибка геокодирования:', error);
      setAddressError('Не удалось получить адрес');
      setAddress(`Координаты: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
    } finally {
      setIsGeocodingAddress(false);
    }
  }, []);

  // Обработчик изменения позиции
  const handleLocationSelect = useCallback((lat: number, lng: number) => {
    setSelectedCoordinates([lat, lng]);
    getAddressFromCoordinates(lat, lng);
  }, [getAddressFromCoordinates]);

  // Получаем адрес при открытии диалога
  useEffect(() => {
    if (open) {
      getAddressFromCoordinates(selectedCoordinates[0], selectedCoordinates[1]);
    }
  }, [open, getAddressFromCoordinates, selectedCoordinates]);

  const handleConfirmAddress = async () => {
    if (!selectedCoordinates) return;

    try {
      const deliveryResult = await triggerGetDeliveryCost({
        latitude: selectedCoordinates[0],
        longitude: selectedCoordinates[1],
      }).unwrap();

      const deliveryCost = deliveryResult.delivery_cost || 0;

      onAddressSelect(address, selectedCoordinates, deliveryCost);
      onClose();
    } catch (error) {
      console.error('Ошибка получения стоимости доставки:', error);
      onAddressSelect(address, selectedCoordinates, 0);
      onClose();
    }
  }

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
        
        {addressError && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {addressError}
          </Alert>
        )}
        
        {/* Отображение текущего адреса */}
        <Box sx={{ mb: 2, p: 2, backgroundColor: 'rgba(58, 58, 55, 1)', borderRadius: 2, border: '1px solid #6B7280' }}>
          <Typography variant="body2" color="text.secondary" mb={1}>
            Выбранный адрес:
          </Typography>
          {isGeocodingAddress ? (
            <Box display="flex" alignItems="center" gap={1}>
              <CircularProgress size={16} />
              <Typography variant="body2" color="text.secondary">
                Определяем адрес...
              </Typography>
            </Box>
          ) : (
            <Typography variant="body1" color="text.primary" fontWeight="medium">
              {address || 'Адрес не определен'}
            </Typography>
          )}
        </Box>
        
        <Box
          sx={{
            width: '100%',
            height: 400,
            borderRadius: 2,
            border: '1px solid #4B5563',
            overflow: 'hidden'
          }}
        >
          <MapContainer
            center={selectedCoordinates}
            zoom={13}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={true}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            
            <MapClickHandler onLocationSelect={handleLocationSelect} />
            
            <DraggableMarker
              position={selectedCoordinates}
              onPositionChange={handleLocationSelect}
            />
          </MapContainer>
        </Box>
        
        <Typography variant="caption" color="text.secondary" mt={1} display="block">
          Координаты: {selectedCoordinates[0].toFixed(6)}, {selectedCoordinates[1].toFixed(6)}
        </Typography>
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
          disabled={!selectedCoordinates || isGettingDeliveryCost || isGeocodingAddress}
          sx={{ ml: 2 }}
        >
          {isGettingDeliveryCost ? (
            <>
              <CircularProgress size={16} sx={{ mr: 1 }} />
              Получаем стоимость...
            </>
          ) : (
            'Подтвердить адрес'
          )}
        </Button>
      </DialogActions>
    </Dialog>
  );
}