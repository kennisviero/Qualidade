import { TestBed } from '@angular/core/testing';
import { NgxsModule, Store } from '@ngxs/store';
import { UserStoriesState, UserStoriesStateModel } from './user-stories.state';
import { UserStoriesAction } from './user-stories.actions';

describe('UserStories store', () => {
  let store: Store;
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [NgxsModule.forRoot([UserStoriesState])],
    });

    store = TestBed.inject(Store);
  });

  it('should create an action and add an item', () => {
    const expected: UserStoriesStateModel = {
      items: ['item-1'],
    };
    store.dispatch(new UserStoriesAction('item-1'));
    const actual = store.selectSnapshot(UserStoriesState.getState);
    expect(actual).toEqual(expected);
  });
});
