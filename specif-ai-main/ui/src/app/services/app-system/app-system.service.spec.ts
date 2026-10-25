import { TestBed } from '@angular/core/testing';

import { AppSystemService } from './app-system.service';

describe('AppSystemService', () => {
  let service: AppSystemService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(AppSystemService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
