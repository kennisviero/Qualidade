import { IBreadcrumb } from '../../model/interfaces/projects.interface';

export class AddBreadcrumb {
  static readonly type = '[Breadcrumb] Add item';

  constructor(readonly payload: IBreadcrumb) {}
}

export class AddBreadcrumbs {
  static readonly type = '[Breadcrumb] Add items';

  constructor(readonly payload: IBreadcrumb[]) {}
}

export class SetBreadcrumb {
  static readonly type = '[Breadcrumb] Update item';

  constructor(readonly payload: IBreadcrumb) {}
}

export class DeleteBreadcrumb {
  static readonly type = '[Breadcrumb] Delete item';

  constructor(readonly payload: string) {}
}

