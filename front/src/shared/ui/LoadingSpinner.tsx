import React from 'react';
import { Box, CircularProgress } from '@mui/material';

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 40, 
  className = '' 
}) => {
  return (
    <Box 
      display="flex" 
      justifyContent="center" 
      alignItems="center" 
      py={4}
      className={className}
    >
      <CircularProgress size={size} sx={{ color: 'primary.main' }} />
    </Box>
  );
};