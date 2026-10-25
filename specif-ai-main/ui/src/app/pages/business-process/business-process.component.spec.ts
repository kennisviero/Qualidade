import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BusinessProcessComponent } from './business-process.component';

describe('BusinessProcessComponent', () => {
  let component: BusinessProcessComponent;
  let fixture: ComponentFixture<BusinessProcessComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [BusinessProcessComponent]
    });
    fixture = TestBed.createComponent(BusinessProcessComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
