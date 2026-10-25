import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EditSolutionComponent } from './edit-solution.component';

describe('EditSolutionComponent', () => {
  let component: EditSolutionComponent;
  let fixture: ComponentFixture<EditSolutionComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [EditSolutionComponent]
    });
    fixture = TestBed.createComponent(EditSolutionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
