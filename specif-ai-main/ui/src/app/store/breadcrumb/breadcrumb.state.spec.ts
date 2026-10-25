import { TestBed } from '@angular/core/testing';
import {  NgxsModule,  Store } from '@ngxs/store';
import { BreadcrumbState, BreadcrumbStateModel } from './breadcrumb.state';
import { BreadcrumbAction } from './breadcrumb.actions';

describe('Breadcrumb store', () => {
  let store: Store;
  beforeEach(() => {
    TestBed.configureTestingModule({
       imports: [NgxsModule.forRoot([BreadcrumbState])] 
    });

    store = TestBed.inject(Store);
  });

  it('should create an action and add an item', () => {
    const expected: BreadcrumbStateModel = {
      items: ['item-1']
    };
    store.dispatch(new BreadcrumbAction('item-1'));
    const actual = store.selectSnapshot(BreadcrumbState.getState);
    expect(actual).toEqual(expected);
  });

});
