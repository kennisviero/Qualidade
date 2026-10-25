import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserStoriesComponent } from './user-stories.component';

describe('UserStoriesComponent', () => {
  let component: UserStoriesComponent;
  let fixture: ComponentFixture<UserStoriesComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [UserStoriesComponent]
    });
    fixture = TestBed.createComponent(UserStoriesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
