import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/shared/config';
import { Button, type ButtonVariant } from '@/shared/ui';
import { useLogoutMutation } from '../api/authApi';

export function LogoutButton({ variant = 'outline', block }: { variant?: ButtonVariant; block?: boolean }) {
  const [logout, { isLoading }] = useLogoutMutation();
  const navigate = useNavigate();
  return (
    <Button
      variant={variant}
      size="small"
      block={block}
      loading={isLoading}
      onClick={async () => {
        await logout().unwrap().catch(() => undefined);
        navigate(ROUTES.welcome);
      }}
    >
      Выйти
    </Button>
  );
}
