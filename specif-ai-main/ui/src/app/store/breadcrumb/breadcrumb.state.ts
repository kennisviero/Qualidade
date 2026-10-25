import { Injectable } from '@angular/core';
import { State, Action, Selector, StateContext } from '@ngxs/store';
import {
  AddBreadcrumb,
  AddBreadcrumbs,
  DeleteBreadcrumb,
  SetBreadcrumb,
} from './breadcrumb.actions';
import { IBreadcrumb } from '../../model/interfaces/projects.interface';

export interface BreadcrumbStateModel {
  items: IBreadcrumb[];
}

@State<BreadcrumbStateModel>({
  name: 'breadcrumb',
  defaults: {
    items: [],
  },
})
@Injectable()
export class BreadcrumbState {
  @Selector()
  static getBreadcrumbs(state: BreadcrumbStateModel) {
    return state.items;
  }

  @Action(AddBreadcrumb)
  addBreadcrumb(
    ctx: StateContext<BreadcrumbStateModel>,
    { payload }: AddBreadcrumb,
  ) {
    const state = ctx.getState();
    const breadcrumbExists = state.items.some(
      (existingBreadcrumb) => existingBreadcrumb.label === payload.label,
    );
    if (!breadcrumbExists) {
      ctx.patchState({
        items: [...state.items, payload],
      });
    }
  }

  @Action(AddBreadcrumbs)
  addBreadcrumbs(
    ctx: StateContext<BreadcrumbStateModel>,
    { payload }: AddBreadcrumbs,
  ) {
    const state = ctx.getState();
    ctx.patchState({
      items: [...payload],
    });
  }

  @Action(SetBreadcrumb)
  setBreadcrumb(
    ctx: StateContext<BreadcrumbStateModel>,
    { payload }: SetBreadcrumb,
  ) {
    const state = ctx.getState();
    ctx.patchState({
      items: [...state.items, payload],
    });
  }

  @Action(DeleteBreadcrumb)
  deleteBreadcrumb(
    ctx: StateContext<BreadcrumbStateModel>,
    { payload }: DeleteBreadcrumb,
  ) {
    const state = ctx.getState();
    const remainingBreadCrumbs = state.items.filter((breadcrumb) => breadcrumb.label !== payload)
    ctx.patchState({
      items: [...remainingBreadCrumbs],
    });
  }
}
