import { ROUTES } from '@/shared/config';
import { ButtonLink, EmptyState, PageHeader } from '@/shared/ui';

export default function NotFoundPage() {
  return (
    <>
      <PageHeader title="Такой страницы нет" />
      <EmptyState icon="🗂" actions={<ButtonLink to={ROUTES.home} variant="primary" size="small">В кабинет</ButtonLink>}>
        Возможно, ссылка устарела или в адресе опечатка
      </EmptyState>
    </>
  );
}
