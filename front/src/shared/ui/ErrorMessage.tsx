import React from 'react';
import { Alert, Box } from '@mui/material';
import { ErrorOutline } from '@mui/icons-material';

interface ErrorMessageProps {
  message: string;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message }) => {
  return (
    <Box display="flex" justifyContent="center" py={4}>
      <Alert 
        severity="error" 
        icon={<ErrorOutline />}
        sx={{
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid #EF4444',
          borderRadius: 2,
        }}
      >
        {message}
      </Alert>
    </Box>
  );
};