import os

import pytest

# Set required env vars before any imports
if "ANALYSIS_DATABASE__URL" not in os.environ:
    os.environ["ANALYSIS_DATABASE__URL"] = "sqlite+aiosqlite:///./test.db"


# ── Fixtures for domain rule tests ─────────────────────────────────────


@pytest.fixture
def sample_python_functions() -> list[dict[str, object]]:
    return [
        {
            "name": "simple_func",
            "line_start": 1,
            "line_end": 3,
            "snippet": "def simple_func():\n    pass\n",
            "complexity": 1,
        },
        {
            "name": "complex_func",
            "line_start": 10,
            "line_end": 35,
            "snippet": "def complex_func():\n    if a:\n        for b in c:\n            while d:\n                if e:\n                    pass\n",
            "complexity": 5,
        },
        {
            "name": "very_complex",
            "line_start": 40,
            "line_end": 90,
            "snippet": "def very_complex():\n    if a:\n        if b:\n            if c:\n                if d:\n                    if e:\n                        if f:\n                            pass\n",
            "complexity": 7,
        },
    ]


@pytest.fixture
def sample_routes() -> list[dict[str, object]]:
    return [
        {
            "path": "/api/public",
            "method": "GET",
            "has_auth": False,
            "line_start": 1,
            "snippet": 'app.get("/api/public")',
        },
        {
            "path": "/api/secure",
            "method": "GET",
            "has_auth": True,
            "line_start": 5,
            "snippet": '@login_required\napp.get("/api/secure")',
        },
        {
            "path": "/api/data",
            "method": "POST",
            "has_auth": False,
            "line_start": 10,
            "snippet": 'app.post("/api/data")',
        },
    ]


@pytest.fixture
def sample_ast_data(
    sample_python_functions: list[dict[str, object]],
    sample_routes: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "functions": sample_python_functions,
        "routes": sample_routes,
        "classes": [],
        "imports": [],
    }


@pytest.fixture
def sample_content() -> str:
    return "\n".join(
        [
            "import os",
            "import sys",
            "",
            "SECRET_KEY = 'sk-abc123def456ghi'",
            "API_KEY = 'a1b2c3d4e5f6a7b8c9d0e1f2'",
            "",
            "def hello():",
            "    return 'world'",
        ]
    )


# ── Fixtures for parser tests ──────────────────────────────────────────


@pytest.fixture
def csharp_code() -> str:
    return """
using System;
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;

namespace MyApp.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;

    public UsersController(IUserService userService)
    {
        _userService = userService;
    }

    [HttpGet]
    public IActionResult GetAll()
    {
        var users = _userService.GetAll();
        return Ok(users);
    }

    [HttpGet("{id}")]
    public IActionResult GetById(int id)
    {
        var user = _userService.GetById(id);
        if (user == null)
            return NotFound();
        return Ok(user);
    }

    [HttpPost]
    public IActionResult Create([FromBody] UserDto dto)
    {
        var user = _userService.Create(dto);
        return CreatedAtAction(nameof(GetById), new { id = user.Id }, user);
    }
}

public record UserDto(string Name, string Email);

public interface IUserService
{
    List<UserDto> GetAll();
    UserDto? GetById(int id);
    UserDto Create(UserDto dto);
}
"""


@pytest.fixture
def java_code() -> str:
    return """
package com.example.demo;

import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;
import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping
    public List<User> getAll() {
        return userService.findAll();
    }

    @GetMapping("/{id}")
    public User getById(@PathVariable Long id) {
        return userService.findById(id);
    }

    @PostMapping
    public User create(@RequestBody User user) {
        return userService.save(user);
    }
}
"""


@pytest.fixture
def python_code() -> str:
    return """
import os
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hello"}

@router.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
"""


@pytest.fixture
def go_code() -> str:
    return """
package main

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

type User struct {
    Name  string `json:"name"`
    Email string `json:"email"`
}

func main() {
    r := gin.Default()
    r.GET("/users", getUsers)
    r.POST("/users", createUser)
    r.Run()
}

func getUsers(c *gin.Context) {
    c.JSON(http.StatusOK, []User{})
}

func createUser(c *gin.Context) {
    var user User
    c.BindJSON(&user)
    c.JSON(http.StatusCreated, user)
}
"""


@pytest.fixture
def javascript_code() -> str:
    return """
import express from 'express';
const router = express.Router();

router.get('/', (req, res) => {
    res.json({ message: 'Hello' });
});

router.post('/users', (req, res) => {
    res.status(201).json(req.body);
});

export default router;
"""
