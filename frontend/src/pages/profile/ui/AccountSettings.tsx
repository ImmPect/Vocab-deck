/** Смена имени и пароля (PATCH /me), удаление аккаунта с подтверждением паролем (DELETE /me). */
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogoutButton } from '@/features/auth';
import { session, useDeleteMeMutation, useUpdateMeMutation, type Me } from '@/entities/user';
import { asApiError, baseApi, fieldErrors } from '@/shared/api';
import { ROUTES } from '@/shared/config';
import { ui, useAppDispatch } from '@/shared/model';
import { Button, Input, Modal, Paper } from '@/shared/ui';
import s from './ProfilePage.module.css';

export function AccountSettings({ me }: { me: Me }) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [update, { isLoading }] = useUpdateMeMutation();
  const [remove, removeState] = useDeleteMeMutation();
  const [name, setName] = useState(me.name);
  const [pwd, setPwd] = useState({ current_password: '', new_password: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [confirm, setConfirm] = useState(false);
  const [delPwd, setDelPwd] = useState('');
  const [delError, setDelError] = useState<string>();

  async function save(e: FormEvent) {
    e.preventDefault();
    const body: Record<string, string> = {};
    if (name.trim() !== me.name) body.name = name.trim();
    if (pwd.new_password) {
      if (pwd.new_password.length < 8) return setErrors({ new_password: 'Не короче 8 символов' });
      Object.assign(body, pwd);
    }
    if (!Object.keys(body).length) return;
    try {
      await update(body).unwrap();
      setPwd({ current_password: '', new_password: '' });
      setErrors({});
      dispatch(ui.toastShown('Изменения сохранены'));
    } catch (err) {
      const api = asApiError(err);
      const fe = fieldErrors(api);
      setErrors(Object.keys(fe).length ? fe : { form: api?.message ?? '' });
    }
  }

  async function deleteAccount() {
    try {
      await remove({ password: delPwd }).unwrap();
      dispatch(session.loggedOut());
      dispatch(baseApi.util.resetApiState());
      dispatch(ui.toastShown('Аккаунт удалён'));
      navigate(ROUTES.welcome, { replace: true });
    } catch (err) {
      const api = asApiError(err);
      setDelError(fieldErrors(api).password ?? api?.message);
    }
  }

  return (
    <Paper as="section" plain className={s.panel} aria-labelledby="settings-title">
      <h2 id="settings-title" className={s.h}>
        Аккаунт
      </h2>
      <form onSubmit={save} noValidate>
        <Input label="Имя" name="name" value={name} error={errors.name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
        <div className={s.row2}>
          <Input label="Текущий пароль" name="current_password" type="password" autoComplete="current-password"
            value={pwd.current_password} error={errors.current_password}
            onChange={(e) => setPwd((p) => ({ ...p, current_password: e.target.value }))} />
          <Input label="Новый пароль" name="new_password" type="password" autoComplete="new-password"
            value={pwd.new_password} error={errors.new_password} hint="Не короче 8 символов"
            onChange={(e) => setPwd((p) => ({ ...p, new_password: e.target.value }))} />
        </div>
        {errors.form && <p className={s.err} role="alert">{errors.form}</p>}
        <div className={s.actions}>
          <Button type="submit" loading={isLoading}>Сохранить</Button>
          <LogoutButton variant="outlinePaper" />
          <Button variant="link" className={s.danger} onClick={() => setConfirm(true)}>Удалить аккаунт</Button>
        </div>
      </form>
      {confirm && (
        <Modal
          title="Удалить аккаунт?"
          onClose={() => setConfirm(false)}
          actions={
            <>
              <Button variant="outlinePaper" onClick={() => setConfirm(false)}>Отмена</Button>
              <Button variant="danger" loading={removeState.isLoading} disabled={!delPwd} onClick={deleteAccount}>Удалить навсегда</Button>
            </>
          }
        >
          <p className={s.text}>Профиль, прогресс и личные списки будут удалены без возможности восстановления.</p>
          <Input label="Пароль для подтверждения" type="password" name="password" autoComplete="current-password"
            value={delPwd} error={delError} onChange={(e) => setDelPwd(e.target.value)} />
        </Modal>
      )}
    </Paper>
  );
}
