package com.demo.validation;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertNotNull;

class DemoApplicationTest {
    @Test
    void applicationClassExists() {
        assertNotNull(new DemoApplication());
    }
}
