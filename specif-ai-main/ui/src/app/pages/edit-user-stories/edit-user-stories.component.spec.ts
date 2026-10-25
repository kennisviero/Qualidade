import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EditUserStoriesComponent } from './edit-user-stories.component';

describe('EditUserStoriesComponent', () => {
  let component: EditUserStoriesComponent;
  let fixture: ComponentFixture<EditUserStoriesComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [EditUserStoriesComponent]
    });
    fixture = TestBed.createComponent(EditUserStoriesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
